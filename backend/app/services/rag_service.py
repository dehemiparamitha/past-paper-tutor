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
    Answer the student's question using ONLY the provided
    university materials.

    If the answer cannot be found in the provided materials,
    say that the information is not available in the uploaded
    materials.

    Explain the answer clearly and in an exam-oriented way.

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


def find_similar_questions(query: str, limit: int = 10) -> list[dict]:
    """Return the closest indexed questions with normalized relevance scores."""
    matches = get_vectorstore().similarity_search_with_relevance_scores(
        query,
        k=limit,
    )

    results = []
    for document, relevance in matches:
        metadata = document.metadata
        results.append(
            {
                "year": metadata.get("paper_year"),
                "question_number": metadata.get("question_number"),
                "question_type": metadata.get("question_type"),
                "question": document.page_content,
                "similarity": round(max(0.0, min(1.0, relevance)), 2),
            }
        )

    return results