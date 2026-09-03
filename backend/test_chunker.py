import sys
from app.rag.loader import load_pdf
from app.rag.chunker import split_questions, chunks_to_langchain_documents

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

pdf_path = "data/past_papers/2016.pdf"
print(f"Loading {pdf_path}...\n")
text = load_pdf(pdf_path)

chunks = split_questions(text, file_path=pdf_path)

print(f"\n=======================================================")
print(f"  PAPER CHUNKING VERIFICATION REPORT")
print(f"=======================================================")
print(f"Paper year detected : {chunks[0]['metadata'].get('paper_year') if chunks else 'N/A'}")
print(f"Total chunks        : {len(chunks)}")
print()

# ── Per-type summary ─────────────────────────────────────────────
by_type = {"mcq": [], "structured_essay": [], "essay": []}
for c in chunks:
    by_type[c["question_type"]].append(c)

expected = {"mcq": 40, "structured_essay": 4, "essay": 5}

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