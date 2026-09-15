from functools import lru_cache

from langchain_chroma import Chroma
from app.rag.embeddings import get_embeddings

PERSIST_DIRECTORY="chroma_db"


@lru_cache(maxsize=1)
def get_vectorstore():
    embeddings = get_embeddings()

    vectorstore = Chroma(
        persist_directory=PERSIST_DIRECTORY,
        embedding_function=embeddings,
        collection_name="past_papers"
    )

    return vectorstore