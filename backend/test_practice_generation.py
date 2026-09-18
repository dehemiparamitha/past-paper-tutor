import sys
import json
from app.services.practice_service import generate_practice_questions, evaluate_student_answer

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


def test_mcq_generation():
    print("\n" + "=" * 70)
    print("TEST 1: GENERATING MCQ PRACTICE QUESTIONS (Light & Optics / Physics)")
    print("=" * 70)

    res = generate_practice_questions(
        topic="geometrical_optics",
        grade=11,
        subject_area="physics",
        question_type="mcq",
        difficulty="medium",
        count=2
    )

    print(f"Success: {res.get('success')}")
    print(f"Topic: {res.get('topic')} | Grade: {res.get('grade')} | Subject: {res.get('subject_area')}")
    print(f"Total Generated: {res.get('total_generated')}")
    print(f"Source References: {res.get('source_references')}")

    questions = res.get("questions", [])
    for idx, q in enumerate(questions, start=1):
        print(f"\n--- [MCQ #{idx}] ---")
        print(f"Question: {q.get('question')}")
        print(f"Options: {q.get('options')}")
        print(f"Correct Answer: {q.get('correct_answer')}")
        print(f"Explanation: {q.get('explanation')}")
        print(f"Hints: {q.get('hints')}")
        print(f"Textbook Concept: {q.get('relevant_textbook_concept')}")


def test_structured_essay_generation():
    print("\n" + "=" * 70)
    print("TEST 2: GENERATING STRUCTURED ESSAY QUESTIONS (Photosynthesis / Biology)")
    print("=" * 70)

    res = generate_practice_questions(
        topic="photosynthesis",
        grade=11,
        subject_area="biology",
        question_type="structured_essay",
        difficulty="medium",
        count=1
    )

    print(f"Success: {res.get('success')}")
    print(f"Topic: {res.get('topic')} | Grade: {res.get('grade')} | Subject: {res.get('subject_area')}")
    print(f"Total Generated: {res.get('total_generated')}")

    questions = res.get("questions", [])
    for idx, q in enumerate(questions, start=1):
        print(f"\n--- [Structured Question #{idx}] ---")
        print(f"Question:\n{q.get('question')}")
        print(f"\nModel Answer:\n{q.get('model_answer')}")
        print(f"\nMarking Scheme:\n{json.dumps(q.get('marking_scheme'), indent=2)}")
        print(f"Total Marks: {q.get('total_marks')}")


def test_student_answer_evaluation():
    print("\n" + "=" * 70)
    print("TEST 3: EVALUATING STUDENT STRUCTURED ANSWER")
    print("=" * 70)

    question = "State two factors necessary for photosynthesis and name the primary pigment involved."
    model_answer = "Factors: Light (or Sunlight), Carbon dioxide, Water. Pigment: Chlorophyll."
    marking_scheme = [
        {"point": "Any two factors (Light, CO2, Water)", "marks": 2},
        {"point": "Chlorophyll stated as the pigment", "marks": 1}
    ]
    student_ans = "Sunlight and water are needed. The green pigment is chlorophyll."

    eval_res = evaluate_student_answer(
        question=question,
        student_answer=student_ans,
        model_answer=model_answer,
        question_type="structured_essay",
        marking_scheme=marking_scheme,
        total_marks=3
    )

    print(f"Marks Awarded: {eval_res.get('marks_awarded')}/{eval_res.get('total_possible_marks')}")
    print(f"Percentage: {eval_res.get('percentage')}%")
    print(f"Is Fully Correct: {eval_res.get('is_fully_correct')}")
    print(f"Feedback: {eval_res.get('feedback')}")
    print(f"Point Breakdown:\n{json.dumps(eval_res.get('point_breakdown'), indent=2)}")


if __name__ == "__main__":
    test_mcq_generation()
    test_structured_essay_generation()
    test_student_answer_evaluation()
