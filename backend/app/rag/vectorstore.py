from functools import lru_cache

from langchain_chroma import Chroma
from app.rag.embeddings import get_embeddings
from app.config.settings import settings


@lru_cache(maxsize=1)
def get_vectorstore():
    persist_dir = getattr(settings, "CHROMA_PERSIST_DIRECTORY", "chroma_db") or "chroma_db"
    embeddings = get_embeddings()

    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="past_papers"
    )

    return vectorstore
