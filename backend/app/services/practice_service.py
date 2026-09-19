import json
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.rag.vectorstore import get_vectorstore
from app.services.rag_service import (
    retrieve_textbook_content,
    find_similar_questions,
    TOPIC_METADATA_REGISTRY,
    _clean_question_text,
)

load_dotenv()

# Initialize LLM for practice question generation
practice_llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    temperature=0.3,
)

eval_llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    temperature=0.0,
)

PRACTICE_GENERATION_PROMPT = ChatPromptTemplate.from_template(
    """
You are an expert Sri Lankan G.C.E. Ordinary Level (O/L) Science paper setter and senior examiner.
Your goal is to generate brand-new, syllabus-compliant, high-quality practice questions for O/L students.

TARGET SPECIFICATIONS:
- Subject: Science (Sri Lankan G.C.E. O/L)
- Grade: {grade}
- Subject Area: {subject_area}
- Syllabus Topic: {topic}
- Target Question Type: {question_type} (MCQ, Structured Essay, or Essay)
- Difficulty Level: {difficulty} (Easy, Medium, or Hard)
- Number of Questions to Generate: {count}

THEORY & CONCEPTUAL CONTEXT (From Grade {grade} Science Textbooks):
{textbook_context}

AUTHENTIC PAST PAPER QUESTION EXEMPLARS (Use these for style, phrasing, and exam standard):
{past_paper_exemplars}

INSTRUCTIONS:
1. Generate strictly {count} questions adhering to the Sri Lankan G.C.E. O/L standard.
2. Ground all facts, definitions, units, and principles firmly in the provided textbook context.
3. For MCQ:
   - Provide exactly 4 options formatted as: "1) ...", "2) ...", "3) ...", "4) ...".
   - Ensure only ONE option is unequivocally correct.
   - Distractors should test common student misconceptions.
4. For Structured Essay / Essay:
   - Break down into standard O/L sub-parts: (a), (b), (i), (ii), etc.
   - Indicate marks for each subpart in square brackets, e.g. [1 mark], [2 marks].
   - Ensure the total marks for a structured question conform to standard O/L allocations (e.g. 5 to 15 marks).
5. For every question, provide:
   - "model_answer": A complete, ideal student answer.
   - "marking_scheme": A list of discrete marking points with mark allocations [{{"point": "...", "marks": 1}}, ...].
   - "explanation": Clear conceptual explanation citing scientific laws or textbook reasoning.
   - "hints": 1-2 constructive hints to help a struggling student without giving away the full answer.
   - "relevant_textbook_concept": Specific chapter/topic concept tested.

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this exact structure (no commentary, no conversational preamble):
{{
  "topic": "{topic}",
  "grade": {grade},
  "subject_area": "{subject_area}",
  "question_type": "{question_type}",
  "difficulty": "{difficulty}",
  "total_generated": {count},
  "questions": [
    {{
      "id": 1,
      "question": "Question text here...",
      "question_type": "mcq",
      "options": ["1) Option A", "2) Option B", "3) Option C", "4) Option D"],
      "correct_answer": "1) Option A",
      "model_answer": "Full model answer here...",
      "marking_scheme": [
        {{"point": "Key point 1", "marks": 1}},
        {{"point": "Key point 2", "marks": 1}}
      ],
      "total_marks": 2,
      "explanation": "Detailed explanation here...",
      "hints": ["Hint 1", "Hint 2"],
      "relevant_textbook_concept": "Concept name"
    }}
  ]
}}
"""
)

EVALUATION_PROMPT = ChatPromptTemplate.from_template(
    """
You are a senior Sri Lankan G.C.E. Ordinary Level (O/L) Science examiner evaluating a student's answer.

QUESTION DETAILS:
Question: {question}
Question Type: {question_type}
Model Answer: {model_answer}
Marking Scheme: {marking_scheme}
Total Possible Marks: {total_marks}

STUDENT SUBMISSION:
{student_answer}

INSTRUCTIONS:
1. Objectively evaluate the student's answer against each point in the marking scheme.
2. Award marks based on scientific accuracy, correct keywords, proper formulas, and units.
3. For MCQ: If student selected the correct option, award full marks (1/1); otherwise 0.
4. For Structured / Essay: Award partial marks point-by-point according to the marking scheme.
5. Provide constructive, encouraging feedback explaining what was correct and what was missing or inaccurate.

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "marks_awarded": 0,
  "total_possible_marks": {total_marks},
  "percentage": 0.0,
  "is_fully_correct": false,
  "point_breakdown": [
    {{
      "point": "Marking scheme requirement",
      "marks_allocated": 1,
      "marks_awarded": 1,
      "student_performance": "Student met this point accurately."
    }}
  ],
  "feedback": "Encouraging and precise feedback...",
  "key_improvements": ["List of 1-3 specific scientific points to review"]
}}
"""
)


def _normalize_llm_content(content: Any) -> str:
    """Safely converts LLM response content into a clean string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
            elif hasattr(block, "text"):
                text_parts.append(getattr(block, "text"))
            else:
                text_parts.append(str(block))
        return "".join(text_parts)
    return str(content)


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """Extracts and parses a JSON object from raw LLM output text."""
    # Attempt 1: Regex matching { ... }
    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except Exception:
            pass

    # Attempt 2: Strip markdown codeblocks
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def generate_practice_questions(
    topic: str,
    grade: Optional[int] = None,
    subject_area: Optional[str] = None,
    question_type: str = "mcq",
    difficulty: str = "medium",
    count: int = 3,
) -> Dict[str, Any]:
    """
    Generates practice questions grounded in textbook theory and past paper exam styles.
    """
    # 1. Resolve metadata from TOPIC_METADATA_REGISTRY if not supplied
    normalized_topic_key = topic.strip().lower().replace(" ", "_").replace("-", "_")
    meta_info = TOPIC_METADATA_REGISTRY.get(normalized_topic_key, {})

    effective_grade = grade or meta_info.get("grade", 10)
    effective_subject = subject_area or meta_info.get("subject_area", "general")
    effective_count = max(1, min(10, count))
    effective_qtype = question_type.lower() if question_type in ["mcq", "structured_essay", "essay"] else "mcq"
    effective_difficulty = difficulty.capitalize() if difficulty.lower() in ["easy", "medium", "hard"] else "Medium"

    # 2. Retrieve textbook context (Theory & Scientific Facts)
    textbook_chunks = retrieve_textbook_content(query=topic, k=4)
    if textbook_chunks:
        textbook_context = "\n\n".join([
            f"[Grade {c.get('grade', effective_grade)} Textbook (Page {c.get('page_number', 'N/A')})]:\n{c.get('content', '')}"
            for c in textbook_chunks
        ])
    else:
        textbook_context = f"Standard Sri Lankan G.C.E. O/L Grade {effective_grade} Science syllabus curriculum on {topic}."

    # 3. Retrieve past paper exemplars (Exam Style & Question Structure)
    past_paper_matches = find_similar_questions(
        query=topic,
        question_type=effective_qtype if effective_qtype != "any" else None,
        limit=3
    )
    if past_paper_matches:
        past_paper_exemplars = "\n\n---\n\n".join([
            f"[Past Paper {q.get('year', 'Exam')} - Q{q.get('question_number', '')} ({q.get('question_type', '').upper()})]:\n{q.get('question', '')}"
            for q in past_paper_matches
        ])
    else:
        past_paper_exemplars = "No direct past paper exemplar matched. Formulate questions conforming strictly to the G.C.E. O/L examination standards."

    # 4. Invoke LLM to generate questions
    human_topic_display = topic.replace("_", " ").title()
    try:
        response = PRACTICE_GENERATION_PROMPT.format_prompt(
            grade=effective_grade,
            subject_area=effective_subject,
            topic=human_topic_display,
            question_type=effective_qtype,
            difficulty=effective_difficulty,
            count=effective_count,
            textbook_context=textbook_context,
            past_paper_exemplars=past_paper_exemplars,
        )
        llm_output = practice_llm.invoke(response.to_messages())
        raw_text = _normalize_llm_content(llm_output.content).strip()
        parsed = _extract_json_object(raw_text)

        if parsed and "questions" in parsed and isinstance(parsed["questions"], list):
            # Ensure each question has an ID and clean formatting
            for idx, q in enumerate(parsed["questions"], start=1):
                q["id"] = q.get("id", idx)
                q["question_type"] = q.get("question_type", effective_qtype)
                if effective_qtype == "mcq" and "options" in q:
                    # Guarantee options is a list
                    if not isinstance(q["options"], list):
                        q["options"] = []
                # Ensure marking_scheme has proper fallback
                if "marking_scheme" not in q or not isinstance(q["marking_scheme"], list):
                    q["marking_scheme"] = [{"point": q.get("model_answer", "Correct answer"), "marks": q.get("total_marks", 1)}]
                if "total_marks" not in q:
                    q["total_marks"] = sum(item.get("marks", 1) for item in q["marking_scheme"])

            return {
                "success": True,
                "topic": human_topic_display,
                "grade": effective_grade,
                "subject_area": effective_subject,
                "question_type": effective_qtype,
                "difficulty": effective_difficulty,
                "total_generated": len(parsed["questions"]),
                "questions": parsed["questions"],
                "source_references": {
                    "textbook_chunks_used": len(textbook_chunks),
                    "past_paper_exemplars_used": len(past_paper_matches)
                }
            }
        else:
            # Fallback if JSON parsing returned empty
            return _generate_fallback_response(
                topic=human_topic_display,
                grade=effective_grade,
                subject_area=effective_subject,
                question_type=effective_qtype,
                difficulty=effective_difficulty,
                raw_text=raw_text
            )

    except Exception as e:
        print(f"Error generating practice questions: {e}")
        return {
            "success": False,
            "error": str(e),
            "topic": human_topic_display,
            "grade": effective_grade,
            "subject_area": effective_subject,
            "questions": []
        }


def evaluate_student_answer(
    question: str,
    student_answer: str,
    model_answer: str,
    question_type: str = "mcq",
    marking_scheme: Optional[List[Dict[str, Any]]] = None,
    total_marks: int = 1,
) -> Dict[str, Any]:
    """
    Evaluates a student's answer against the marking scheme and model answer.
    """
    # 1. Quick evaluation for MCQ
    if question_type.lower() == "mcq":
        clean_student = student_answer.strip().lower()
        clean_model = model_answer.strip().lower()

        # Check if option number or text matches
        student_opt = re.search(r"\b([1-4])\b", clean_student)
        model_opt = re.search(r"\b([1-4])\b", clean_model)

        is_correct = False
        if student_opt and model_opt and student_opt.group(1) == model_opt.group(1):
            is_correct = True
        elif clean_student in clean_model or clean_model in clean_student:
            is_correct = True

        marks_awarded = 1 if is_correct else 0
        return {
            "success": True,
            "marks_awarded": marks_awarded,
            "total_possible_marks": 1,
            "percentage": 100.0 if is_correct else 0.0,
            "is_fully_correct": is_correct,
            "feedback": "Correct! Well done." if is_correct else f"Incorrect. The correct option is: {model_answer}",
            "point_breakdown": [
                {
                    "point": "Select the correct MCQ option",
                    "marks_allocated": 1,
                    "marks_awarded": marks_awarded,
                    "student_performance": "Correct option selected." if is_correct else "Incorrect option selected."
                }
            ],
            "key_improvements": [] if is_correct else ["Review the fundamental definition in your textbook."]
        }

    # 2. LLM evaluation for Structured Essay / Essay
    scheme_str = json.dumps(marking_scheme or [{"point": model_answer, "marks": total_marks}], indent=2)
    try:
        response = EVALUATION_PROMPT.format_prompt(
            question=question,
            question_type=question_type,
            model_answer=model_answer,
            marking_scheme=scheme_str,
            total_marks=total_marks,
            student_answer=student_answer,
        )
        llm_output = eval_llm.invoke(response.to_messages())
        raw_text = _normalize_llm_content(llm_output.content).strip()
        parsed = _extract_json_object(raw_text)

        if parsed:
            parsed["success"] = True
            return parsed
        else:
            return {
                "success": True,
                "marks_awarded": 0,
                "total_possible_marks": total_marks,
                "percentage": 0.0,
                "is_fully_correct": False,
                "feedback": raw_text or "Answer evaluated.",
                "point_breakdown": [],
                "key_improvements": []
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "marks_awarded": 0,
            "total_possible_marks": total_marks,
            "feedback": "Error evaluating answer."
        }


def _generate_fallback_response(
    topic: str,
    grade: int,
    subject_area: str,
    question_type: str,
    difficulty: str,
    raw_text: str
) -> Dict[str, Any]:
    """Generates a structured fallback response if LLM returned non-JSON text."""
    return {
        "success": True,
        "topic": topic,
        "grade": grade,
        "subject_area": subject_area,
        "question_type": question_type,
        "difficulty": difficulty,
        "total_generated": 1,
        "questions": [
            {
                "id": 1,
                "question": f"Practice question on {topic} ({difficulty} difficulty):\n{raw_text[:300]}",
                "question_type": question_type,
                "options": ["1) Option A", "2) Option B", "3) Option C", "4) Option D"] if question_type == "mcq" else [],
                "correct_answer": "1) Option A" if question_type == "mcq" else "",
                "model_answer": "Refer to the textbook theory chapter for the detailed step-by-step solution.",
                "marking_scheme": [{"point": "Correct conceptual answer with units", "marks": 1}],
                "total_marks": 1,
                "explanation": "Derived directly from the syllabus core learning outcomes.",
                "hints": ["Check the key definitions and formulas in your notes."],
                "relevant_textbook_concept": topic
            }
        ],
        "source_references": {"textbook_chunks_used": 0, "past_paper_exemplars_used": 0}
    }


def record_practice_attempt(
    db: Any,
    question_id: Any,
    student_answer: str,
    evaluation_result: Dict[str, Any],
    user_id: Optional[Any] = None,
) -> Optional[Any]:
    """Persists a practice attempt to the PostgreSQL database if available."""
    try:
        from app.models.practice import PracticeAttempt, TopicMastery
        from app.models.question import Question
        import uuid

        marks_awarded = float(evaluation_result.get("marks_awarded", 0.0))
        total_marks = float(evaluation_result.get("total_possible_marks", 1.0))
        pct = float(evaluation_result.get("percentage", 0.0))
        is_corr = "yes" if pct >= 80.0 else ("partial" if pct > 0 else "no")
        feedback = evaluation_result.get("feedback", "")

        q_uuid = uuid.UUID(str(question_id)) if isinstance(question_id, (str, uuid.UUID)) else None
        if not q_uuid:
            return None

        attempt = PracticeAttempt(
            user_id=user_id,
            question_id=q_uuid,
            student_answer=student_answer,
            is_correct=is_corr,
            marks_awarded=marks_awarded,
            total_possible_marks=total_marks,
            percentage=pct,
            ai_feedback=feedback,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return attempt
    except Exception:
        db.rollback()
        return None
