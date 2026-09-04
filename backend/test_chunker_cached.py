import os
import sys
from app.rag.chunker import split_questions, chunks_to_langchain_documents

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

year_arg = sys.argv[1] if len(sys.argv) > 1 else "2015"
year_str = os.path.basename(year_arg).replace("extracted_text_", "").replace(".txt", "").replace(".pdf", "")

txt_file = f"extracted_text_{year_str}.txt"
if not os.path.exists(txt_file):
    print(f"Cached text file {txt_file} not found.")
    sys.exit(1)

with open(txt_file, "r", encoding="utf-8") as f:
    text = f.read()

pdf_path = f"data/past_papers/{year_str}.pdf"
chunks = split_questions(text, file_path=pdf_path)

print("=======================================================")
print(f"  PAPER CHUNKING VERIFICATION REPORT ({year_str} INSTANT)")
print("=======================================================")
year = chunks[0]['metadata'].get('paper_year') if chunks else None
print(f"Paper year detected : {year if year else 'N/A'}")
print(f"Total chunks        : {len(chunks)}\n")

by_type = {"mcq": [], "structured_essay": [], "essay": []}
for c in chunks:
    by_type[c["question_type"]].append(c)

essay_found_nums = [c["question_number"] for c in by_type["essay"]]
expected_essay_count = 6 if (year == 2015 or 10 in essay_found_nums or len(by_type["essay"]) == 6) else 5

expected = {"mcq": 40, "structured_essay": 4, "essay": expected_essay_count}

print(f"{'TYPE':<22} {'FOUND':>5}  {'EXPECTED':>8}  {'STATUS':>8}")
print("-" * 50)
for q_type, expected_count in expected.items():
    found = len(by_type[q_type])
    status = "✓ OK" if found == expected_count else "✗ MISMATCH"
    print(f"{q_type:<22} {found:>5}  {expected_count:>8}  {status:>8}")

print()
for q_type in ["mcq", "structured_essay", "essay"]:
    q_nums = [c["question_number"] for c in by_type[q_type]]
    print(f"[{q_type.upper():<16}] {len(q_nums)} questions: {q_nums}")

mcq_nums = sorted(c["question_number"] for c in by_type["mcq"])
expected_mcq = list(range(1, 41))
missing = [n for n in expected_mcq if n not in mcq_nums]
dupes = [n for n in mcq_nums if mcq_nums.count(n) > 1]

print()
if missing:
    print(f"⚠ Missing MCQ questions : {missing}")
else:
    print("✓ No missing MCQ questions (1–40 all present)")

if dupes:
    print(f"⚠ Duplicate MCQ numbers : {sorted(set(dupes))}")
else:
    print("✓ No duplicate MCQ question numbers")

docs = chunks_to_langchain_documents(chunks)
print(f"\n✓ Successfully converted {len(docs)} chunks to LangChain Documents for ChromaDB.")
