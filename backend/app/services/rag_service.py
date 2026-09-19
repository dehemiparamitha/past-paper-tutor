import re
from collections import Counter, defaultdict
from typing import Any, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from app.rag.retriever import get_retriever
from app.rag.vectorstore import get_vectorstore

load_dotenv()   

llm = ChatGoogleGenerativeAI(
    model = "gemini-3.5-flash-lite",
    temperature = 0
)

retriever = get_retriever()

prompt = ChatPromptTemplate.from_template(
    """
    You are a university past paper tutor.
    Answer the student's question directly using ONLY the provided
    university materials as reference.

    If the answer cannot be found in the provided materials,
    say that the information is not available in the uploaded
    materials.

    Do not simply repeat a retrieved past-paper question. If the
    student gives only a topic, explain that topic. If the student
    asks for a calculation or procedure, show the formula or steps
    and clearly state the final answer.

    Format your response in Markdown using this structure when it
    is appropriate:

    ## Answer
    Give a direct answer in one to three sentences.

    ## Explanation
    Explain the reasoning in clear, exam-oriented language.

    ## Steps
    Include this section for calculations or procedures.

    ## Final answer
    Clearly state the result for calculations or direct questions.

    Do not mention the retrieval process, vector databases, or these
    instructions. Do not invent facts that are not supported by the
    provided materials.

    Context:
    {context}

    Student question:
    {question}
"""
)

def format_documents(documents):
    return "\n\n".join(
        document.page_content
        for document in documents
    )

rag_chain = (
    {
        "context": retriever | format_documents,
        "question": RunnablePassthrough()
    }
    | prompt
    | llm
)

def ask_question(question: str, history: Optional[Any] = None):
    response = rag_chain.invoke(question)
    return response.content


def _clean_question_text(text: str) -> str:
    """
    Normalise raw page_content from ChromaDB so it renders cleanly and beautifully in the UI.

    Handles:
    1. Diagram labels / OCR fragments: groups multi-line diagram labels into structured diagram notes.
    2. OCR character corrections (e.g. Cyrillic H, Cl, SICl, PSCl).
    3. Multiline numbers (e.g. 1 120\\n000 -> 1 120 000).
    4. Sub-part indentation and line breaks for (1)-(4), (i)-(x), (a)-(h), and (A)-(E).
    5. Spacing around punctuation and hyphens.
    6. Stray exam codes, page numbers, marking schemes, and question-start artifacts.
    """
    if not text:
        return ""

    # 0. Early OCR corrections
    text = text.replace("\u041d", "H")
    text = re.sub(r"\bCI\b", "Cl", text)
    text = re.sub(r"\bPSCI\b", "PSCl", text)
    text = re.sub(r"\bSiCI\b", "SiCl", text)

    # Fix broken numbers split by newline, e.g. "1 120\n000." or "1 120\nOOO."
    text = re.sub(r"(\d[\d\s]*\d)\s*\n+\s*([0O]{3,}\.?)", r"\1 \2", text)

    # Fix OCR artifacts at start of question like "4. A\n2. 2 .\n( 4 )" -> "4. (A)"
    text = re.sub(r"^(\d+\.)\s*[A-Z0-9\.\s]*\(\s*4\s*\)", r"\1 (A)", text)
    text = re.sub(r"\n(\d+\.)\s*[A-Z0-9\.\s]*\(\s*4\s*\)", r"\n\1 (A)", text)
    text = re.sub(r"^(\d+\.)\s*\(\s*4\s*\)", r"\1 (A)", text)

    # 1. Remove [DIAGRAM: ...] tags
    text = re.sub(r"\[DIAGRAM:[^\]]*\]", "", text, flags=re.DOTALL)

    # 2. Collapse spaced brackets: ( X ) -> (X), ( 1 ) -> (1), ( i ) -> (i), ( a ) -> (a), etc.
    text = re.sub(r"\(\s+([^\s()]{1,8})\s+\)", r"(\1)", text)

    # Remove trailing exam marks indicator e.g. ( 20 marks ) or (20 marks)
    text = re.sub(r"\s*\(\s*\d+\s*marks\s*\)\s*$", "", text, flags=re.IGNORECASE)

    # 3. Filter stray page-footers, exam codes, and lone numbers
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Lone number or dash-number-dash e.g. "15", "-4-", "-3-"
        if re.fullmatch(r"-?\s*\d+\s*-?", stripped):
            continue
        # Stray line numbers like "9. 9 ." or "2. 2 ."
        if re.fullmatch(r"\d+\.\s*\d+\s*\.?", stripped):
            continue
        # Exam codes like "OL / 2025 ( 2026 ) / 34 / E - I"
        if re.search(r"\bOL\b.*\d{4}", stripped, re.IGNORECASE):
            continue
        cleaned_lines.append(stripped)

    # 4. Strict sub-part vs diagram label detection:
    # Valid sections: (A)-(E), MCQs: (1)-(4), Roman: (i)-(x), Alpha: (a)-(h)
    valid_subpart_pattern = re.compile(
        r"^\((?:[1-4]|[a-h]|(?:viii|vii|vi|iv|iii|ii|ix|x|v|i)|[A-E])\)\s*",
        re.IGNORECASE,
    )
    question_start_pattern = re.compile(r"^\d+\.\s*", re.IGNORECASE)

    def is_diagram_or_fragment_line(l: str) -> bool:
        if valid_subpart_pattern.match(l) or question_start_pattern.match(l):
            return False
        # If line ends with question mark or is a long sentence, it's normal question text
        if l.endswith("?") or len(l) > 40:
            return False
        return True

    # Group diagram label fragments into structured diagram lines
    processed_lines = []
    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]
        if is_diagram_or_fragment_line(line):
            cluster = []
            while i < len(cleaned_lines) and is_diagram_or_fragment_line(cleaned_lines[i]):
                cluster.append(cleaned_lines[i])
                i += 1

            if cluster:
                # Deduplicate identical adjacent items
                deduped = []
                for item in cluster:
                    cleaned_item = item.strip("- .")
                    if cleaned_item and (not deduped or deduped[-1] != cleaned_item):
                        deduped.append(cleaned_item)

                if deduped:
                    label_str = ", ".join(deduped)
                    processed_lines.append(f"[Diagram / Figure: {label_str}]")
        else:
            processed_lines.append(line)
            i += 1

    text = "\n".join(processed_lines)

    # 5. Ensure sections, sub-parts, and MCQ options start on their own lines
    # Sections (A), (B), (C), (D), (E)
    text = re.sub(r"(?<!^)\s*\(([A-E])\)\s*", r"\n\n(\1) ", text)

    # MCQ options (1), (2), (3), (4)
    text = re.sub(r"(?<!^)\s*\(([1-4])\)\s*", r"\n  (\1) ", text)

    # Essay roman numerals: (i), (ii), (iii), (iv), (v), (vi), (vii), (viii), (ix), (x)
    roman = r"(?:viii|vii|vi|iv|iii|ii|ix|x|v|i)"
    text = re.sub(
        rf"(?:(?<=\.)|(?<=\?)|(?<=:)|(?<=\n)|^)\s*\((?={roman}\))({roman})\)\s*",
        r"\n  (\1) ",
        text,
        flags=re.IGNORECASE,
    )

    # Essay alpha subparts: (a), (b), (c), (d), (e), (f), (g), (h)
    text = re.sub(
        r"(?:(?<=\.)|(?<=\?)|(?<=:)|(?<=\n)|^)\s*\((?=[a-h]\))([a-h])\)\s*",
        r"\n    (\1) ",
        text,
    )

    # Handle subparts directly adjacent to section headers or roman numerals e.g. "(A) (i)" or "(ii) (a)"
    text = re.sub(
        rf"(\([A-E]\))\s*\((?={roman}\))({roman})\)\s*",
        r"\1\n  (\2) ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"(\({roman}\))\s*\((?=[a-h]\))([a-h])\)\s*",
        r"\1\n    (\2) ",
        text,
        flags=re.IGNORECASE,
    )

    # 6. Fix punctuation and spacing
    # Spacing before punctuation: 'word ?' -> 'word?'
    text = re.sub(r"\s+([?!,;:])", r"\1", text)
    # Trailing periods on questions: '?. ' -> '? '
    text = re.sub(r"\?\.", "?", text)
    # Hyphenated words: 'p - n' -> 'p-n', 'sub - circuit' -> 'sub-circuit'
    text = re.sub(r"(\b[A-Za-z0-9]+)\s*-\s*([A-Za-z0-9]+\b)", r"\1-\2", text)

    # 7. Clean question start: "6. (A)" on one line
    text = re.sub(r"^(\d+\.)\s*\n+(\([A-E]\))", r"\1 \2", text, flags=re.MULTILINE)
    text = re.sub(r"^(\d+\.)\s*\n+", r"\1 ", text, flags=re.MULTILINE)

    # 8. Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
    

def extract_metadata_filters(query: str) -> tuple[str, dict[str, Any]]:
    """
    Extracts year ranges, specific years, and question types from natural language queries,
    and returns the cleaned topic query alongside any extracted filters.

    Examples:
    - "Show recursion questions between 2018 and 2024" -> ("Show recursion questions", {"start_year": 2018, "end_year": 2024})
    - "Show light questions in 2019" -> ("Show light questions", {"year": 2019})
    - "MCQ questions on electricity from 2015 to 2020" -> ("questions on electricity", {"start_year": 2015, "end_year": 2020, "question_type": "mcq"})
    """
    filters: dict[str, Any] = {}
    cleaned = query

    # 1. Year range: "between 2018 and 2024", "from 2018 to 2024", "2018-2024", "2018 to 2024"
    range_match = re.search(
        r"\b(?:between|from)?\s*(\d{4})\s*(?:and|to|-|–)\s*(\d{4})\b",
        cleaned,
        re.IGNORECASE,
    )
    if range_match:
        y1, y2 = int(range_match.group(1)), int(range_match.group(2))
        filters["start_year"] = min(y1, y2)
        filters["end_year"] = max(y1, y2)
        cleaned = cleaned[: range_match.start()] + " " + cleaned[range_match.end() :]

    # 2. Year comparison: "after 2018", "since 2018", "before 2024", "until 2024"
    if "start_year" not in filters:
        after_match = re.search(r"\b(?:after|since|from)\s+(\d{4})\b", cleaned, re.IGNORECASE)
        if after_match:
            filters["start_year"] = int(after_match.group(1))
            cleaned = cleaned[: after_match.start()] + " " + cleaned[after_match.end() :]

    if "end_year" not in filters:
        before_match = re.search(r"\b(?:before|until|up\s+to)\s+(\d{4})\b", cleaned, re.IGNORECASE)
        if before_match:
            filters["end_year"] = int(before_match.group(1))
            cleaned = cleaned[: before_match.start()] + " " + cleaned[before_match.end() :]

    # 3. Single year: "in 2020", "for 2020", "2020 paper"
    if "start_year" not in filters and "end_year" not in filters:
        single_year_match = re.search(r"\b(?:in|for)?\s*(20\d{2})\s*(?:paper|exam)?\b", cleaned, re.IGNORECASE)
        if single_year_match:
            filters["year"] = int(single_year_match.group(1))
            cleaned = cleaned[: single_year_match.start()] + " " + cleaned[single_year_match.end() :]

    # 4. Question type extraction
    if re.search(r"\bmcq(?:s)?\b", cleaned, re.IGNORECASE):
        filters["question_type"] = "mcq"
        cleaned = re.sub(r"\bmcq(?:s)?\b", "", cleaned, flags=re.IGNORECASE)
    elif re.search(r"\bstructured\s+essay(?:s)?\b", cleaned, re.IGNORECASE):
        filters["question_type"] = "structured_essay"
        cleaned = re.sub(r"\bstructured\s+essay(?:s)?\b", "", cleaned, flags=re.IGNORECASE)
    elif re.search(r"\bessay(?:s)?\b", cleaned, re.IGNORECASE):
        filters["question_type"] = "essay"
        cleaned = re.sub(r"\bessay(?:s)?\b", "", cleaned, flags=re.IGNORECASE)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, filters


def build_chroma_filter(
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    year: Optional[int] = None,
    question_type: Optional[str] = None,
    has_diagram: Optional[bool] = None,
) -> Optional[dict[str, Any]]:
    """
    Constructs a valid ChromaDB compound filter dictionary using $and operators.
    Supports year range ($gte, $lte), exact year, and question_type.
    """
    conditions: list[dict[str, Any]] = []

    if year is not None:
        conditions.append({"paper_year": year})
    else:
        if start_year is not None and end_year is not None and start_year == end_year:
            conditions.append({"paper_year": start_year})
        else:
            if start_year is not None:
                conditions.append({"paper_year": {"$gte": start_year}})
            if end_year is not None:
                conditions.append({"paper_year": {"$lte": end_year}})

    if question_type:
        conditions.append({"question_type": question_type})

    if has_diagram is not None:
        conditions.append({"has_diagram": has_diagram})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _extract_search_topic(query: str) -> str:
    """Strip conversational phrasing so vector search focuses on the actual subject topic."""
    patterns = [
        r"^(?:what are|show me|show|find|give me|give|provide me|provide|list|tell me|search for|can you find|can you show|display|get)\s*(?:the\s+)?(?:all\s+)?(?:similar|related|past paper|exam)?\s*questions?\s*(?:on|about|regarding|related to|for)?\s*",
        r"^(?:questions?\s+(?:on|about|regarding|related to)\s*)",
    ]
    cleaned = query.strip()
    for p in patterns:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"[?!.,;]+$", "", cleaned).strip()
    return cleaned if len(cleaned) >= 2 else query


def find_similar_questions(
    query: str,
    limit: int = 5,
    min_score: float = 0.10,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    year: Optional[int] = None,
    question_type: Optional[str] = None,
) -> list[dict]:
    """
    Return questions that are genuinely relevant to the query topic with optional metadata filtering.

    Applies:
    1. Automatic extraction of year ranges or question types from natural queries.
    2. ChromaDB metadata filter application (year range, exact year, question type).
    3. Conversational intent stripping to isolate the core subject keywords.
    4. Absolute relevance score threshold (min_score) to filter out unrelated papers.
    5. Adaptive drop-off cutoff relative to the top match score.
    """
    cleaned_query, extracted_filters = extract_metadata_filters(query)

    # Explicit arguments override query-parsed filters
    eff_start_year = start_year if start_year is not None else extracted_filters.get("start_year")
    eff_end_year = end_year if end_year is not None else extracted_filters.get("end_year")
    eff_year = year if year is not None else extracted_filters.get("year")
    eff_question_type = question_type if question_type is not None else extracted_filters.get("question_type")

    topic = _extract_search_topic(cleaned_query)
    vectorstore = get_vectorstore()

    chroma_filter = build_chroma_filter(
        start_year=eff_start_year,
        end_year=eff_end_year,
        year=eff_year,
        question_type=eff_question_type,
    )

    search_kwargs: dict[str, Any] = {"k": limit * 2}
    if chroma_filter:
        search_kwargs["filter"] = chroma_filter

    # Search with the cleaned topic
    matches = vectorstore.similarity_search_with_relevance_scores(topic, **search_kwargs)

    # Fallback search with cleaned query if cleaned topic returned no strong matches
    if (not matches or matches[0][1] < min_score) and topic != cleaned_query and cleaned_query:
        fallback_matches = vectorstore.similarity_search_with_relevance_scores(cleaned_query, **search_kwargs)
        if fallback_matches and (not matches or fallback_matches[0][1] > matches[0][1]):
            matches = fallback_matches

    if not matches:
        return []

    best_score = matches[0][1]
    if best_score < min_score:
        return []

    results = []
    for document, relevance in matches:
        if relevance < min_score:
            continue
        # Drop candidates that fall too far below the top match score
        if relevance < best_score * 0.35 and len(results) >= 1:
            continue

        metadata = document.metadata
        # Skip textbook chunks when retrieving past paper questions
        if metadata.get("doc_type") == "textbook" or not metadata.get("paper_year"):
            continue

        results.append(
            {
                "year": metadata.get("paper_year"),
                "question_number": metadata.get("question_number"),
                "question_type": metadata.get("question_type"),
                "question": _clean_question_text(document.page_content),
                "similarity": round(max(0.0, min(1.0, relevance)), 2),
            }
        )

        if len(results) >= limit:
            break

    return results


TOPIC_METADATA_REGISTRY: dict[str, dict[str, Any]] = {
    # Grade 10 Physics
    "motion_in_a_straight_line": {"grade": 10, "subject_area": "physics"},
    "newtons_laws_of_motion": {"grade": 10, "subject_area": "physics"},
    "friction": {"grade": 10, "subject_area": "physics"},
    "resultant_force": {"grade": 10, "subject_area": "physics"},
    "turning_effect_of_a_force": {"grade": 10, "subject_area": "physics"},
    "equilibrium_of_forces": {"grade": 10, "subject_area": "physics"},
    "hydrostatic_pressure_and_its_applications": {"grade": 10, "subject_area": "physics"},
    "work_energy_and_power": {"grade": 10, "subject_area": "physics"},
    "current_electricity": {"grade": 10, "subject_area": "physics"},
    # Grade 10 Chemistry
    "structure_of_matter": {"grade": 10, "subject_area": "chemistry"},
    "quantification_of_elements_and_compounds": {"grade": 10, "subject_area": "chemistry"},
    "chemical_bonds": {"grade": 10, "subject_area": "chemistry"},
    "change_in_matter": {"grade": 10, "subject_area": "chemistry"},
    "rate_of_reaction": {"grade": 10, "subject_area": "chemistry"},
    # Grade 10 Biology
    "chemical_basis_of_life": {"grade": 10, "subject_area": "biology"},
    "structure_and_functions_of_cells": {"grade": 10, "subject_area": "biology"},
    "characteristics_of_organisms": {"grade": 10, "subject_area": "biology"},
    "the_world_of_life": {"grade": 10, "subject_area": "biology"},
    "continuity_of_life": {"grade": 10, "subject_area": "biology"},
    "inheritance": {"grade": 10, "subject_area": "biology"},
    # Grade 11 Physics
    "waves_and_their_applications": {"grade": 11, "subject_area": "physics"},
    "geometrical_optics": {"grade": 11, "subject_area": "physics"},
    "heat": {"grade": 11, "subject_area": "physics"},
    "power_and_energy_of_electric_appliances": {"grade": 11, "subject_area": "physics"},
    "electronics": {"grade": 11, "subject_area": "physics"},
    "electromagnetism_and_electromagnetic_induction": {"grade": 11, "subject_area": "physics"},
    # Grade 11 Chemistry
    "mixtures": {"grade": 11, "subject_area": "chemistry"},
    "acids_bases_and_salts": {"grade": 11, "subject_area": "chemistry"},
    "heat_changes_associated_with_chemical_reactions": {"grade": 11, "subject_area": "chemistry"},
    "electrochemistry": {"grade": 11, "subject_area": "chemistry"},
    "hydrocarbons_and_their_derivatives": {"grade": 11, "subject_area": "chemistry"},
    # Grade 11 Biology
    "living_tissues": {"grade": 11, "subject_area": "biology"},
    "photosynthesis": {"grade": 11, "subject_area": "biology"},
    "biological_processes_in_human_body": {"grade": 11, "subject_area": "biology"},
    "biosphere": {"grade": 11, "subject_area": "biology"},
}


def get_topic_frequency(
    year: Optional[int] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Aggregates question frequency per topic across all papers or within a specific year range.
    Returns a sorted list of dicts: [{"topic": "geometrical_optics", "grade": 11, "subject_area": "physics", "count": 5}, ...]
    """
    vectorstore = get_vectorstore()
    collection = vectorstore._collection

    chroma_filter = build_chroma_filter(year=year, start_year=start_year, end_year=end_year)

    if chroma_filter:
        data = collection.get(where=chroma_filter, include=["metadatas"])
    else:
        data = collection.get(include=["metadatas"])

    metadatas = data.get("metadatas", []) or []
    topics = [
        meta.get("topic")
        for meta in metadatas
        if meta and meta.get("topic")
    ]

    topic_grade_map: dict[str, int] = {}
    topic_subject_map: dict[str, str] = {}
    for meta in metadatas:
        t = meta.get("topic")
        if t:
            meta_info = TOPIC_METADATA_REGISTRY.get(t, {})
            if t not in topic_grade_map:
                topic_grade_map[t] = meta.get("grade") or meta_info.get("grade", 10)
            if t not in topic_subject_map:
                topic_subject_map[t] = meta.get("subject_area") or meta_info.get("subject_area", "general")

    counter = Counter(topics)

    return [
        {
            "topic": topic,
            "grade": topic_grade_map.get(topic, TOPIC_METADATA_REGISTRY.get(topic, {}).get("grade", 10)),
            "subject_area": topic_subject_map.get(topic, TOPIC_METADATA_REGISTRY.get(topic, {}).get("subject_area", "general")),
            "count": count,
        }
        for topic, count in counter.most_common()
    ]


def get_topic_trends(topic: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Computes yearly trend statistics for each topic across all available papers.
    Returns:
    [
        {
            "topic": "geometrical_optics",
            "grade": 11,
            "subject_area": "physics",
            "total_questions": 18,
            "yearly_breakdown": {"2018": 3, "2019": 2, "2020": 4, "2021": 4, "2022": 5},
            "trend": "rising" | "declining" | "stable"
        },
        ...
    ]
    """
    vectorstore = get_vectorstore()
    collection = vectorstore._collection

    data = collection.get(include=["metadatas"])
    metadatas = data.get("metadatas", []) or []

    if not metadatas:
        return []

    # Map: topic -> year -> count
    topic_year_map = defaultdict(lambda: defaultdict(int))
    topic_subject_map: dict[str, str] = {}
    topic_grade_map: dict[str, int] = {}
    all_years = set()

    for m in metadatas:
        t = m.get("topic")
        y = m.get("paper_year")
        s = m.get("subject_area")
        g = m.get("grade")
        if t and y:
            y_int = int(y)
            topic_year_map[t][y_int] += 1
            all_years.add(y_int)
            meta_info = TOPIC_METADATA_REGISTRY.get(t, {})
            if t not in topic_subject_map:
                topic_subject_map[t] = s or meta_info.get("subject_area", "general")
            if t not in topic_grade_map:
                topic_grade_map[t] = g or meta_info.get("grade", 10)

    if not all_years:
        return []

    sorted_years = sorted(list(all_years))
    results = []

    for t_name, yearly_counts in topic_year_map.items():
        if topic and t_name.lower() != topic.lower():
            continue

        counts_by_year = {str(y): yearly_counts.get(y, 0) for y in sorted_years}
        total = sum(yearly_counts.values())

        # Determine trend direction (comparing last 2 available years to earlier)
        values = [yearly_counts.get(y, 0) for y in sorted_years]
        if len(values) >= 3:
            recent_avg = sum(values[-2:]) / 2.0
            earlier_avg = sum(values[:-2]) / float(len(values) - 2)
            if recent_avg > earlier_avg * 1.25 and recent_avg > 0:
                trend = "rising"
            elif recent_avg < earlier_avg * 0.75:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        meta_info = TOPIC_METADATA_REGISTRY.get(t_name, {})
        results.append({
            "topic": t_name,
            "grade": topic_grade_map.get(t_name, meta_info.get("grade", 10)),
            "subject_area": topic_subject_map.get(t_name, meta_info.get("subject_area", "general")),
            "total_questions": total,
            "yearly_breakdown": counts_by_year,
            "trend": trend,
        })

    return sorted(results, key=lambda x: x["total_questions"], reverse=True)


def calculate_important_topics() -> list[dict[str, Any]]:
    """
    Computes an empirical Importance Index (0-100) for every syllabus topic using 4 dimensions:
    1. Frequency (30%): Total question volume relative to top topic
    2. Recency (25%): Questions appearing in recent exam years weighted higher
    3. Consistency (25%): Percentage of past paper years where this topic appeared
    4. Marks / Depth (20%): Weighted marks by question type (MCQ=1, Structured=5, Essay=10)
    """
    vectorstore = get_vectorstore()
    collection = vectorstore._collection

    data = collection.get(include=["metadatas"])
    metadatas = data.get("metadatas", []) or []

    if not metadatas:
        return []

    # 1. Gather baseline year range
    all_years = sorted(list({int(m["paper_year"]) for m in metadatas if m.get("paper_year")}))
    if not all_years:
        return []

    total_years_count = len(all_years)
    min_year = all_years[0]
    max_year = all_years[-1]
    year_span = max(1, max_year - min_year)

    # Weights by question format
    TYPE_WEIGHTS = {"mcq": 1, "structured_essay": 5, "essay": 10}

    topic_stats = defaultdict(lambda: {
        "total_count": 0,
        "years": set(),
        "weighted_marks": 0,
        "recency_sum": 0.0,
        "subject_area": "general",
        "grade": 10,
    })

    for m in metadatas:
        t = m.get("topic")
        y = m.get("paper_year")
        q_type = m.get("question_type", "mcq")
        subj = m.get("subject_area")
        gr = m.get("grade")

        if not t or not y:
            continue

        year_int = int(y)
        stats = topic_stats[t]
        stats["total_count"] += 1
        stats["years"].add(year_int)
        
        meta_info = TOPIC_METADATA_REGISTRY.get(t, {})
        stats["subject_area"] = subj or meta_info.get("subject_area", stats["subject_area"])
        stats["grade"] = gr or meta_info.get("grade", stats["grade"])

        stats["weighted_marks"] += TYPE_WEIGHTS.get(q_type, 1)

        # Recency scale: 1.0 (oldest year) to 3.0 (newest year)
        recency_factor = 1.0 + 2.0 * ((year_int - min_year) / year_span)
        stats["recency_sum"] += recency_factor

    if not topic_stats:
        return []

    # 2. Maximum values for normalization
    max_count = max((s["total_count"] for s in topic_stats.values()), default=1)
    max_marks = max((s["weighted_marks"] for s in topic_stats.values()), default=1)
    max_recency = max((s["recency_sum"] for s in topic_stats.values()), default=1.0)

    results = []
    for topic_name, s in topic_stats.items():
        # Component scores (0-100 scale)
        freq_score = (s["total_count"] / max_count) * 100
        consistency_score = (len(s["years"]) / total_years_count) * 100
        recency_score = (s["recency_sum"] / max_recency) * 100
        marks_score = (s["weighted_marks"] / max_marks) * 100

        # Weighted Composite Score (0-100)
        final_score = round(
            (0.30 * freq_score)
            + (0.25 * recency_score)
            + (0.25 * consistency_score)
            + (0.20 * marks_score)
        )

        if final_score >= 75:
            tier = "High"
            badge = "🔥 Highly Important"
        elif final_score >= 50:
            tier = "Moderate"
            badge = "🟡 Moderate"
        else:
            tier = "Low"
            badge = "🟢 Low"

        results.append({
            "topic": topic_name,
            "grade": s["grade"],
            "subject_area": s["subject_area"],
            "importance_score": final_score,
            "tier": tier,
            "badge": badge,
            "breakdown": {
                "frequency_score": round(freq_score),
                "recency_score": round(recency_score),
                "consistency_score": round(consistency_score),
                "marks_score": round(marks_score),
            },
            "total_questions": s["total_count"],
            "years_appeared": len(s["years"]),
            "total_years_evaluated": total_years_count,
        })

    return sorted(results, key=lambda x: x["importance_score"], reverse=True)


def retrieve_textbook_content(query: str, k: int = 5) -> list[dict[str, Any]]:
    """
    Retrieves relevant textbook theory chunks for a given topic or query from ChromaDB.
    """
    vectorstore = get_vectorstore()
    try:
        results = vectorstore.similarity_search(
            query,
            k=k,
            filter={"doc_type": "textbook"}
        )
    except Exception:
        results = vectorstore.similarity_search(query, k=k)

    formatted = []
    for doc in results:
        meta = doc.metadata or {}
        formatted.append({
            "content": doc.page_content,
            "grade": meta.get("grade"),
            "source": meta.get("source"),
            "page_number": meta.get("page_number"),
            "topic": meta.get("topic")
        })
    return formatted