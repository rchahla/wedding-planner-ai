import os
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOCS_FOLDER = os.path.join(BASE_DIR, "data", "source_docs")
CHROMA_PATH = os.path.join(BASE_DIR, "data", "chroma_db")
COLLECTION_NAME = "wedding_docs"

model = SentenceTransformer("all-MiniLM-L6-v2")
client = PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)


def load_documents():
    docs = []
    for filename in os.listdir(DOCS_FOLDER):
        file_path = os.path.join(DOCS_FOLDER, filename)

        if os.path.isfile(file_path) and filename.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                docs.append({
                    "id": filename,
                    "text": text,
                    "source": filename
                })
    return docs


def ingest_documents():
    existing = collection.get()
    existing_ids = set(existing["ids"]) if existing["ids"] else set()

    docs = load_documents()
    if not docs:
        return

    new_docs = [doc for doc in docs if doc["id"] not in existing_ids]
    if not new_docs:
        return

    ids = [doc["id"] for doc in new_docs]
    texts = [doc["text"] for doc in new_docs]
    embeddings = model.encode(texts).tolist()
    metadatas = [{"source": doc["source"]} for doc in new_docs]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )


def retrieve_relevant_docs(query, top_k=2):
    query_embedding = model.encode([query]).tolist()[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    retrieved = []
    for doc_text, metadata in zip(documents, metadatas):
        if metadata is None:
            metadata = {}

        retrieved.append({
            "text": doc_text,
            "source": metadata.get("source", "Unknown source")
        })

    return retrieved