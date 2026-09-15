import re
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

def ask_question(question: str):
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


def find_similar_questions(query: str, limit: int = 5, min_score: float = 0.10) -> list[dict]:
    """
    Return questions that are genuinely relevant to the query topic.

    Applies:
    1. Conversational intent stripping to isolate the core subject keywords.
    2. Absolute relevance score threshold (min_score) to filter out unrelated papers.
    3. Adaptive drop-off cutoff relative to the top match score.
    """
    topic = _extract_search_topic(query)
    vectorstore = get_vectorstore()

    # Search with the cleaned topic
    matches = vectorstore.similarity_search_with_relevance_scores(topic, k=limit * 2)

    # Fallback search with original query if cleaned topic returned no strong matches
    if (not matches or matches[0][1] < min_score) and topic != query:
        fallback_matches = vectorstore.similarity_search_with_relevance_scores(query, k=limit * 2)
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