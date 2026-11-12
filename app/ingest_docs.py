# app/ingest_docs.py

import os
import re
import uuid
import hashlib

from pathlib import Path

from docling.document_converter import DocumentConverter

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from urllib.parse import urlparse
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    FilterSelector,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_ROOT = PROJECT_ROOT / "documents"

QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333",
)

# Separate school collection. Do not mix old company data into it.
COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "madinps_docs",
)

WEBSITE_DOMAIN = "madinps.edu.in"
ALLOWED_WEBSITE_PATHS = {
    # Main school information
    "/",
    "/about/",
    "/about-madin/",
    "/vision-and-mission/",
    "/principals-message/",
    "/leadership-236/",
    "/about/mandatory-public-disclosure/",
    "/about/privacy-policy/",

    # Admissions and academics
    "/admission/",
    "/academics/",
    "/academics/academic-calendar/",
    "/academics/school-transfer-certificate-tc/",
    "/career/",

    # Campus and facilities
    "/campus/",
    "/academic-facilities/",
    "/boarding-facilities/",
    "/healthcare-facilities/",
    "/safety-and-security/",
    "/digital-classroom/",
    "/robotic-lab-stem-education/",
    "/science-laboratory/",

    # Student activities
    "/activities/",
    "/co-curriculars/",
    "/football-club/",
    "/skating-club/",
    "/taekwondo-martial-arts/",

    # Transport (public information; verify rates/routes)
    "/transportation-facility/",

    # Contact and public feedback
    "/contact-us/",
    "/testimonial/",

    # School news and events
    "/news/",
    "/news-events/",
    "/exhibition-organized-on-engineers-day/",
    "/kiddiegala/",
    "/election/",
    "/madin-public-school-students-celebrate-student-police-cadet-day-with-enthusiasm/",
    "/mobile-science-exhibition-sparks-curiosity-among-students/",
    "/new-students-welcomed-with-sapling-distribution-at-madin-public-school/",
    "/school-celebrates-77th-independence-day-with-message-of-unity-and-responsibility/",
    "/school-embarks-on-new-academic-year-with-tilawa-quran-study-launch/",
    "/successful-conclusion-of-three-day-artorium-at-school/",
    "/visual-arts-and-science-exhibition/",
    "/vlog/",
}


# Keep this false for the school-only knowledge base.
# Set true only if you intentionally add private department documents.
INCLUDE_DEPARTMENT_DOCUMENTS = (
    os.getenv("INCLUDE_DEPARTMENT_DOCUMENTS", "false").lower()
    == "true"
)


def get_website_url(text):
    """Read the source URL written by the crawler."""

    match = re.search(
        r"source_url:\s*(https?://[^\s]+)",
        text,
        flags=re.IGNORECASE,
    )

    return match.group(1).strip() if match else None


def load_documents():
    converter = DocumentConverter()
    documents = []

    for file_path in DOCUMENTS_ROOT.rglob("*"):

        if not file_path.is_file():
            continue

        extension = file_path.suffix.lower()

        if extension not in {
            ".pdf",
            ".docx",
            ".pptx",
            ".md",
            ".txt",
        }:
            continue

        relative_path = file_path.relative_to(
            DOCUMENTS_ROOT
        )

        is_website_document = (
            len(relative_path.parts) >= 3
            and relative_path.parts[0] == "Websites"
            and relative_path.parts[1] == "madinps"
        )

        if not is_website_document and not INCLUDE_DEPARTMENT_DOCUMENTS:
            continue

        if extension in {".md", ".txt"}:
            text = file_path.read_text(
                encoding="utf-8"
            )
        else:
            result = converter.convert(str(file_path))
            text = result.document.export_to_markdown()

        if not text.strip():
            continue

        if is_website_document:

            source_url = get_website_url(text)

            if not source_url:
                print(
                    f"Skipping website document without source URL: "
                    f"{relative_path}"
                )
                continue
            # Validate the source domain.
            parsed_url = urlparse(source_url)
            if parsed_url.hostname != WEBSITE_DOMAIN:
                print(f"Skipping external URL: {source_url}")
                continue
            # Normalize and validate the website path.
            website_path = parsed_url.path or "/"
            if not website_path.endswith("/"):
                website_path += "/"

            if website_path not in ALLOWED_WEBSITE_PATHS:
                print(
                    f"Skipping website document with disallowed path: {website_path}"
                )
                continue

            metadata = {
                "source": relative_path.as_posix(),
                "url": source_url,
                "domain": WEBSITE_DOMAIN,
                "department": "Public",
                "access_scope": "authenticated",
                "allowed_roles": [],
                "content_type": "website",
            }

        else:

            # Preserve the existing department-based RBAC model.
            department = relative_path.parts[0]

            if department == "General":
                allowed_roles = ["Employee", "C-Level"]
            else:
                allowed_roles = [department, "C-Level"]

            metadata = {
                "source": relative_path.as_posix(),
                "department": department,
                "allowed_roles": allowed_roles,
                "content_type": "department_document",
            }

        documents.append(
            Document(
                page_content=text,
                metadata=metadata,
            )
        )

    return documents


def make_chunk_id(document, index):
    """Generate a stable Qdrant ID for a document chunk."""

    source = document.metadata.get("source", "")
    content_hash = hashlib.sha256(
        document.page_content.encode("utf-8")
    ).hexdigest()

    identity = f"{source}:{index}:{content_hash}"

    return str(
        uuid.uuid5(uuid.NAMESPACE_URL, identity)
    )


def main():

    print("Loading documents...")

    documents = load_documents()

    if not documents:
        raise RuntimeError(
            "No eligible documents found. Run the website crawler first."
        )

    print(f"Original documents: {len(documents)}")

    for index, document in enumerate(documents, start=1):
        print(
            f"\nDocument {index}\n"
            f"Source: {document.metadata.get('source')}\n"
            f"URL: {document.metadata.get('url', 'N/A')}\n"
            f"Characters: {len(document.page_content)}"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
    )

    chunks = splitter.split_documents(documents)

    print(f"\nTotal chunks: {len(chunks)}")

    embeddings = HuggingFaceEmbeddings(
        model_name=os.getenv(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
    )

    client = QdrantClient(url=QDRANT_URL)

    collection_exists = client.collection_exists(
        collection_name=COLLECTION_NAME
    )

    if not collection_exists:

        print(
            f"\nCreating new Qdrant collection: {COLLECTION_NAME}"
        )

        # First ingestion: create the collection.
        QdrantVectorStore.from_documents(
            chunks,
            embeddings,
            url=QDRANT_URL,
            collection_name=COLLECTION_NAME,
            force_recreate=True,
        )

    else:

        print(
            f"\nUpdating existing collection: {COLLECTION_NAME}"
        )

        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            collection_name=COLLECTION_NAME,
            url=QDRANT_URL,
        )

        # Remove only the old Ma'din website pages.
        # Other document types in this collection are untouched.
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.domain",
                            match=MatchValue(
                                value=WEBSITE_DOMAIN
                            ),
                        )
                    ]
                )
            ),
            wait=True,
        )

        ids = [
            make_chunk_id(document, index)
            for index, document in enumerate(chunks)
        ]

        vector_store.add_documents(
            documents=chunks,
            ids=ids,
        )

    print(
        f"\nSuccessfully indexed {len(chunks)} chunks "
        f"into {COLLECTION_NAME}."
    )


if __name__ == "__main__":
    main()