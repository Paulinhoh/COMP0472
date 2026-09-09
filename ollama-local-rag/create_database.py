from langchain_community.document_loaders import DirectoryLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
import os
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
FAISS_PATH = os.environ.get("RAG_FAISS_PATH", str(PROJECT_DIR / "faiss"))
DATA_PATH = os.environ.get(
    "RAG_DATA_PATH",
    str(PROJECT_DIR / "dados" / "documentos_ativos"),
)


def main():
    generate_data_store()


def generate_data_store():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_faiss(chunks)


def load_documents():
    # Carregar arquivos .txt
    loader_txt = DirectoryLoader(DATA_PATH, glob="*.txt")
    documents = loader_txt.load()
    
    # Carregar arquivos .md
    loader_md = DirectoryLoader(DATA_PATH, glob="*.md")
    documents.extend(loader_md.load())
    
    return documents


def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    if chunks:
        document = chunks[min(10, len(chunks) - 1)]
        print(document.page_content)
        print(document.metadata)

    return chunks


def save_to_faiss(chunks: list[Document]):
    # Clear out the database first.
    if os.path.exists(FAISS_PATH):
        shutil.rmtree(FAISS_PATH)

    # Initilize embedding model
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Create a new DB from the documents.
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_PATH)
    print(f"Saved {len(chunks)} chunks to {FAISS_PATH}.")


if __name__ == "__main__":
    main()
