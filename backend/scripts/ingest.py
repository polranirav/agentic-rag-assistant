"""
Data Ingestion Pipeline: PDFs → Chunks → Embeddings → Pinecone

This script processes documents and creates a searchable knowledge base.
"""

import os
import sys
from pathlib import Path
from typing import List
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

from core.config import settings

# Load environment variables
load_dotenv()


def load_documents(directory: str) -> List[Document]:
    """
    Load all PDFs and text files from directory and subdirectories.
    
    Supports:
    - PDF files (.pdf)
    - Text files (.txt)
    - Markdown files (.md)
    
    Recursively searches all subdirectories for better organization.
    """
    
    documents = []
    path = Path(directory)
    
    if not path.exists():
        print(f"❌ Directory not found: {directory}")
        return documents
    
    # Recursively find all PDFs in directory and subdirectories
    pdf_files = list(path.rglob("*.pdf"))
    txt_files = list(path.rglob("*.txt"))
    md_files = list(path.rglob("*.md"))
    
    # Exclude README.md files
    md_files = [f for f in md_files if f.name != "README.md"]
    
    print(f"\n📁 Scanning directory structure...")
    print(f"   Found {len(pdf_files)} PDF files")
    print(f"   Found {len(txt_files)} TXT files")
    print(f"   Found {len(md_files)} MD files")
    print()
    
    # Load PDFs
    for file_path in pdf_files:
        relative_path = file_path.relative_to(path)
        print(f"📄 Loading PDF: {relative_path}")
        try:
            loader = PyPDFLoader(str(file_path))
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = str(relative_path)
                doc.metadata["file_type"] = "pdf"
                doc.metadata["folder"] = str(relative_path.parent)
            documents.extend(docs)
            print(f"   ✅ Loaded {len(docs)} pages")
        except Exception as e:
            print(f"   ❌ Error loading {relative_path}: {e}")
    
    # Load text files
    for file_path in txt_files:
        relative_path = file_path.relative_to(path)
        print(f"📄 Loading TXT: {relative_path}")
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = str(relative_path)
                doc.metadata["file_type"] = "txt"
                doc.metadata["folder"] = str(relative_path.parent)
            documents.extend(docs)
            print(f"   ✅ Loaded {len(docs)} documents")
        except Exception as e:
            print(f"   ❌ Error loading {relative_path}: {e}")
    
    # Load markdown files
    for file_path in md_files:
        relative_path = file_path.relative_to(path)
        print(f"📄 Loading MD: {relative_path}")
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = str(relative_path)
                doc.metadata["file_type"] = "markdown"
                doc.metadata["folder"] = str(relative_path.parent)
            documents.extend(docs)
            print(f"   ✅ Loaded {len(docs)} documents")
        except Exception as e:
            print(f"   ❌ Error loading {relative_path}: {e}")
    
    total_chars = sum(len(d.page_content) for d in documents)
    print(f"\n✅ Total: {len(documents)} documents ({total_chars:,} characters)")
    
    return documents


def chunk_documents(docs: List[Document]) -> List[Document]:
    """
    Split documents into optimal chunks.
    
    Strategy:
    - Chunk size: 1500 characters (optimal for embeddings)
    - Overlap: 300 characters (preserves context at boundaries)
    - Separators: Paragraphs, sentences, words
    """
    
    print("\n🔨 Chunking documents...")
    
    # Recursive character splitter with smart separators
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    
    split_docs = []
    
    for i, doc in enumerate(docs):
        try:
            # Split document
            chunks = text_splitter.split_documents([doc])
            
            # Add metadata to each chunk
            for j, chunk in enumerate(chunks):
                chunk.metadata["chunk_id"] = j
                chunk.metadata["total_chunks"] = len(chunks)
                chunk.metadata["chunk_index"] = f"{i}-{j}"
                if "source" not in chunk.metadata:
                    chunk.metadata["source"] = doc.metadata.get("source", "unknown")
            
            split_docs.extend(chunks)
            
        except Exception as e:
            print(f"⚠️  Chunk error for document {i}: {e}, skipping")
            continue
    
    print(f"✅ Split into {len(split_docs)} chunks")
    print(f"   Average chunk size: {sum(len(d.page_content) for d in split_docs) / len(split_docs):.0f} chars")
    
    return split_docs


def embed_and_upsert(docs: List[Document], namespace: str = "default"):
    """
    Convert chunks to embeddings and store in Pinecone.
    
    Creates index if it doesn't exist.
    """
    
    print("\n🚀 Embedding and uploading to Pinecone...")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key
    )
    
    # Add metadata
    for i, doc in enumerate(docs):
        if not doc.metadata:
            doc.metadata = {}
        doc.metadata["ingested_at"] = datetime.now().isoformat()
        doc.metadata["embedding_model"] = settings.openai_embedding_model
    
    # Initialize Pinecone
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index_name = settings.pinecone_index_name
    
    # Check if index exists
    existing_indexes = pc.list_indexes().names()
    
    if index_name not in existing_indexes:
        print(f"📌 Creating Pinecone index: {index_name}")
        
        # Determine dimension based on embedding model
        dimension = 1536 if "small" in settings.openai_embedding_model else 3072
        
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=settings.pinecone_environment
            )
        )
        
        print(f"   ✅ Index created (dimension: {dimension})")
    else:
        print(f"📌 Using existing index: {index_name}")
    
    # Upsert documents in batches to avoid size limits
    print(f"   Uploading {len(docs)} chunks in batches...")
    
    BATCH_SIZE = 50  # Smaller batches to avoid 4MB limit
    total_batches = (len(docs) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        print(f"   Batch {batch_num}/{total_batches}: uploading {len(batch)} chunks...")
        
        try:
            PineconeVectorStore.from_documents(
                documents=batch,
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
        except Exception as e:
            print(f"   ⚠️ Batch {batch_num} failed: {e}")
            continue
    
    print(f"✅ Upserted {len(docs)} chunks to Pinecone/{namespace}")


def main():
    """Main ingestion pipeline."""
    
    print("=" * 60)
    print("AGENTIC RAG: DATA INGESTION PIPELINE")
    print("=" * 60)
    print()
    
    # Determine data directory - must match upload.py get_data_dir()
    script_dir = Path(__file__).parent  # scripts/
    backend_dir = script_dir.parent     # backend/
    project_root = backend_dir.parent   # agentic-rag-assistant/
    data_dir = project_root.parent / "data" / "raw"  # Same as upload.py
    
    print(f"📁 Data directory: {data_dir}")
    print()
    
    # Step 1: Load documents
    docs = load_documents(str(data_dir))
    
    if not docs:
        print("\n❌ No documents found!")
        print(f"   Please add PDF, TXT, or MD files to: {data_dir}")
        print("\n   Example:")
        print(f"   cp your-document.pdf {data_dir}/")
        return
    
    # Step 2: Chunk documents
    chunked = chunk_documents(docs)
    
    if not chunked:
        print("\n❌ Chunking failed!")
        return
    
    # Step 3: Embed & Upload
    try:
        embed_and_upsert(chunked, namespace="default")
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✅ INGESTION COMPLETE")
    print("=" * 60)
    print("\nYour knowledge base is ready! You can now query it using the agent.")


if __name__ == "__main__":
    main()
