import os
import sys
from app.rag.loader import load_pdf
from app.rag.chunker import split_questions, chunks_to_langchain_documents

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Determine PDF path from CLI argument or default
pdf_arg = sys.argv[1] if len(sys.argv) > 1 else "data/past_papers/2025.pdf"
if not os.path.exists(pdf_arg):
    candidate = os.path.join("data", "past_papers", os.path.basename(pdf_arg))
    if not candidate.endswith(".pdf"):
        candidate += ".pdf"
    if os.path.exists(candidate):
        pdf_path = candidate
    else:
        pdf_path = pdf_arg
else:
    pdf_path = pdf_arg

print(f"Loading {pdf_path}...\n")
text = load_pdf(pdf_path)

chunks = split_questions(text, file_path=pdf_path)

print(f"\n=======================================================")
print(f"  PAPER CHUNKING VERIFICATION REPORT")
print(f"=======================================================")
year = chunks[0]['metadata'].get('paper_year') if chunks else None
print(f"Paper year detected : {year if year else 'N/A'}")
print(f"Total chunks        : {len(chunks)}")
print()

# ── Per-type summary ─────────────────────────────────────────────
by_type = {"mcq": [], "structured_essay": [], "essay": []}
for c in chunks:
    by_type[c["question_type"]].append(c)

# Some years (e.g. 2015, 2017) contain 6 essay questions (Q5 to Q10)
essay_found_nums = [c["question_number"] for c in by_type["essay"]]
expected_essay_count = 6 if (year in (2015, 2017) or 10 in essay_found_nums or len(by_type["essay"]) == 6) else 5

expected = {"mcq": 40, "structured_essay": 4, "essay": expected_essay_count}

print(f"{'TYPE':<22} {'FOUND':>5}  {'EXPECTED':>8}  {'STATUS':>8}")
print("-" * 50)
for q_type, expected_count in expected.items():
    found = len(by_type[q_type])
    status = "✓ OK" if found == expected_count else "✗ MISMATCH"
    print(f"{q_type:<22} {found:>5}  {expected_count:>8}  {status:>8}")

# ── Question numbers found per section ───────────────────────────
print()
for q_type in ["mcq", "structured_essay", "essay"]:
    q_nums = [c["question_number"] for c in by_type[q_type]]
    print(f"[{q_type.upper():<16}] {len(q_nums)} questions: {q_nums}")

# ── Full question list ────────────────────────────────────────────
print()
print(f"{'#':<5} {'TYPE':<20} {'PAGE':>4}  {'DIAGRAM':>7}  STEM (first 65 chars)")
print("-" * 105)
for c in chunks:
    qn   = c["question_number"]
    qtyp = c["question_type"]
    pg   = c["page_number"]
    diag = "YES" if c["has_diagram"] else "-"
    stem = c["stem"].replace("\n", " ")[:65]
    print(f"{qn:<5} {qtyp:<20} {pg:>4}  {diag:>7}  {stem}")

# ── Missing / Duplicate check ────────────────────────────────────
mcq_nums = sorted(c["question_number"] for c in by_type["mcq"])
expected_mcq = list(range(1, 41))
missing  = [n for n in expected_mcq if n not in mcq_nums]
dupes    = [n for n in mcq_nums if mcq_nums.count(n) > 1]

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