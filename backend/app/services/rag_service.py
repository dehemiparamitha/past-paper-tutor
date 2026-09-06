from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from app.rag.retriever import get_retriever

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