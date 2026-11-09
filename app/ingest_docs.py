# Step 8: Create the document ingestion pipeline
# This script reads the department folders, extracts document content, creates chunks, and inserts them into Qdrant.

import os

from pathlib import Path

from docling.document_converter import (
    DocumentConverter,
)

from langchain_core.documents import (
    Document,
)

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from langchain_huggingface import (
    HuggingFaceEmbeddings,
)

from langchain_qdrant import (
    QdrantVectorStore,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parent.parent


DOCUMENTS_ROOT = (
    PROJECT_ROOT / "documents"
)


QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333",
)


COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "company_docs",
)


def main():

    converter = DocumentConverter()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
    )

    documents = []

    for file_path in DOCUMENTS_ROOT.rglob("*"):

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in {
            ".pdf",
            ".docx",
            ".pptx",
            ".md",
            ".txt",
        }:

            continue

        department = file_path.parent.name

        if department == "General":

            allowed_roles = [
                "Employee",
                "C-Level",
            ]

        else:

            allowed_roles = [
                department,
                "C-Level",
            ]

        # Markdown and text can be read directly.
        if file_path.suffix.lower() in {
            ".md",
            ".txt",
        }:

            text = file_path.read_text(
                encoding="utf-8",
            )

        else:

            result = converter.convert(
                str(file_path),
            )

            text = (
                result.document.export_to_markdown()
            )

        if not text.strip():

            continue

        metadata = {
            "source": file_path.relative_to(
                DOCUMENTS_ROOT
            ).as_posix(),

            "department": department,

            "allowed_roles": allowed_roles,
        }

        document = Document(
            page_content=text,
            metadata=metadata,
        )

        documents.append(
            document,
        )

    if not documents:

        raise RuntimeError(
            "No documents found in the documents directory."
        )

    chunks = splitter.split_documents(
        documents,
    )

    embeddings = HuggingFaceEmbeddings(
        model_name=os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
    )

    # Development-only behavior:
    # force_recreate replaces the collection.
    # Do not use this blindly for production ingestion.
    QdrantVectorStore.from_documents(
        chunks,
        embeddings,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
        force_recreate=True,
    )

    print(
        f"Successfully ingested {len(chunks)} chunks."
    )


if __name__ == "__main__":

    main()