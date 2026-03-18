"""
Document Ingestion Script
Reads PDFs and text files from data/ folders, chunks them,
and stores embeddings in ChromaDB (one collection per company).

Usage: python ingest.py
"""

import os
import sys
from pypdf import PdfReader
import chromadb
from app.config import (
    CHROMA_PERSIST_DIR, DATA_DIR,
    COLLECTION_MENSCH, COLLECTION_TYSON,
    CHUNK_SIZE, CHUNK_OVERLAP,
)


def read_pdf(filepath: str) -> str:
    """Extract text from a PDF file. Handles encrypted PDFs gracefully."""
    try:
        reader = PdfReader(filepath)
        if reader.is_encrypted:
            # Try empty password (some PDFs are "encrypted" but readable)
            try:
                reader.decrypt("")
            except Exception:
                print(f"  ⚠️  PDF is encrypted and cannot be decrypted: {filepath}")
                return ""
        text = ""
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as e:
                print(f"  ⚠️  Could not extract page: {e}")
                continue
        return text
    except Exception as e:
        print(f"  ⚠️  Error reading PDF {filepath}: {e}")
        return ""


def read_text_file(filepath: str) -> str:
    """Read a plain text or markdown file."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_documents(folder_path: str) -> list[dict]:
    """Load all documents from a folder. Returns list of {filename, text}."""
    docs = []
    if not os.path.exists(folder_path):
        print(f"  ⚠️  Folder not found: {folder_path}")
        return docs

    for filename in sorted(os.listdir(folder_path)):
        filepath = os.path.join(folder_path, filename)
        if not os.path.isfile(filepath):
            continue

        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        text = ""

        if ext == "pdf":
            text = read_pdf(filepath)
        elif ext in ("txt", "md", "csv", "text"):
            text = read_text_file(filepath)
        elif ext in ("docx",):
            print(f"  ⚠️  DOCX not supported yet, skipping: {filename}")
            continue
        else:
            # Try reading as text
            try:
                text = read_text_file(filepath)
            except Exception:
                print(f"  ⚠️  Cannot read: {filename}, skipping")
                continue

        if text.strip():
            docs.append({"filename": filename, "text": text.strip()})
            print(f"  ✅ Loaded: {filename} ({len(text)} chars)")
        else:
            print(f"  ⚠️  Empty content: {filename}")

    return docs


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at a sentence or paragraph boundary
        if end < len(text):
            # Look for last period, newline, or semicolon in the chunk
            for sep in ["\n\n", "\n", ". ", "; "]:
                last_sep = chunk.rfind(sep)
                if last_sep > chunk_size * 0.5:  # only if past halfway
                    end = start + last_sep + len(sep)
                    chunk = text[start:end]
                    break
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if len(c) > 20]  # filter tiny fragments


def ingest_company(
    company_folder: str,
    collection_name: str,
    chroma_client: chromadb.ClientAPI,
):
    """Load, chunk, and store documents for one company."""
    print(f"\n{'='*50}")
    print(f"Ingesting: {collection_name}")
    print(f"Folder:    {company_folder}")
    print(f"{'='*50}")

    docs = load_documents(company_folder)
    if not docs:
        print(f"  ❌ No documents found in {company_folder}")
        print(f"     Please add PDF/TXT files and re-run.")
        return

    # Delete existing collection if it exists, then create fresh
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    all_chunks = []
    all_ids = []
    all_metadata = []

    for doc in docs:
        chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['filename']}::chunk_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadata.append({
                "source": doc["filename"],
                "company": collection_name,
                "chunk_index": i,
            })

    if all_chunks:
        # ChromaDB will auto-embed using its default model (all-MiniLM-L6-v2)
        # Add in batches to avoid memory issues
        batch_size = 50
        for start in range(0, len(all_chunks), batch_size):
            end = start + batch_size
            collection.add(
                documents=all_chunks[start:end],
                ids=all_ids[start:end],
                metadatas=all_metadata[start:end],
            )
        print(f"  ✅ Stored {len(all_chunks)} chunks in collection '{collection_name}'")
    else:
        print(f"  ❌ No text chunks extracted from documents")


def main():
    print("🔄 Starting document ingestion...")
    print(f"   ChromaDB path: {CHROMA_PERSIST_DIR}")
    print(f"   Data path:     {DATA_DIR}")

    # Initialize ChromaDB with persistent storage
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Ingest each company
    mensch_folder = os.path.join(DATA_DIR, "mensch_und_maschine")
    tyson_folder = os.path.join(DATA_DIR, "tyson_foods")

    ingest_company(mensch_folder, COLLECTION_MENSCH, chroma_client)
    ingest_company(tyson_folder, COLLECTION_TYSON, chroma_client)

    print(f"\n{'='*50}")
    print("✅ Ingestion complete!")
    print(f"   Collections: {[c.name for c in chroma_client.list_collections()]}")
    print(f"   Run the app:  python -m app.main")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
