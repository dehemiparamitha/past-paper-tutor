import sys
from app.rag.loader import load_pdf

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

text = load_pdf("data/past_papers/2025.pdf")

print(text[:5000])

with open("extracted_text_2015.txt", "w", encoding="utf-8") as f:
    f.write(text)
print("\nFull text saved to extracted_text_2015.txt")