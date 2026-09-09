import argparse
import os
import time
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_community.vectorstores import FAISS

FAISS_PATH = os.environ.get("RAG_FAISS_PATH", str(Path(__file__).resolve().parent / "faiss"))

def answer_query(query_text: str, k: int = 4):
    started_at = time.perf_counter()
    llm = OllamaLLM(model="granite4.1:3b", num_predict=128)

    # Initialize embedding model
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Create vector object from local vector store
    vector = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)

    # Set up chain
    prompt = ChatPromptTemplate.from_template("""Answer the following question based only on the provided context:

    <context>
    {context}
    </context>

    Question: {input}""")

    # Retrieve relevant documents for the query.
    retriever = vector.as_retriever(search_kwargs={"k": k})
    documents = retriever.invoke(query_text)
    context = "\n\n".join(document.page_content for document in documents)

    # Invoke the model using the retrieved context.
    response = llm.invoke(prompt.format(context=context, input=query_text))
    return response, time.perf_counter() - started_at, len(documents)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    parser.add_argument("--k", type=int, default=4, help="Number of retrieved chunks.")
    args = parser.parse_args()
    response, _, _ = answer_query(args.query_text, args.k)
    print(response)


if __name__ == "__main__":
    main()