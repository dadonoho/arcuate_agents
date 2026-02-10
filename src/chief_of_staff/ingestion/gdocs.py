"""Google Docs/Drive ingestion — pull documents into the knowledge base."""

from __future__ import annotations

import logging
from typing import Any

from chief_of_staff.communication._google_auth import get_docs_service, get_drive_service
from chief_of_staff.knowledge.store import ingest

logger = logging.getLogger(__name__)


def fetch_and_ingest_docs(folder_id: str | None = None, max_results: int = 50) -> int:
    """Fetch Google Docs and ingest into the knowledge base.

    Args:
        folder_id: Optional Drive folder ID to scope the search.
        max_results: Maximum number of docs to fetch.

    Returns:
        Number of documents ingested.
    """
    drive = get_drive_service()
    docs = get_docs_service()

    # Build query
    query_parts = ["mimeType='application/vnd.google-apps.document'"]
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")

    results = drive.files().list(
        q=" and ".join(query_parts),
        pageSize=max_results,
        fields="files(id, name, modifiedTime, owners)",
    ).execute()

    files = results.get("files", [])
    count = 0

    for file in files:
        try:
            doc = docs.documents().get(documentId=file["id"]).execute()
            content = _extract_doc_text(doc)

            ingest(
                source="gdocs",
                source_id=file["id"],
                title=file["name"],
                content=content,
                metadata={
                    "doc_id": file["id"],
                    "modified": file.get("modifiedTime", ""),
                    "owners": [o.get("displayName", "") for o in file.get("owners", [])],
                },
            )
            count += 1

        except Exception as e:
            logger.error(f"Failed to ingest doc {file['id']} ({file['name']}): {e}")

    logger.info(f"Ingested {count}/{len(files)} Google Docs")
    return count


def _extract_doc_text(doc: dict[str, Any]) -> str:
    """Extract plain text from a Google Docs API document response."""
    text_parts: list[str] = []

    body = doc.get("body", {})
    for element in body.get("content", []):
        paragraph = element.get("paragraph", {})
        for elem in paragraph.get("elements", []):
            text_run = elem.get("textRun", {})
            content = text_run.get("content", "")
            if content:
                text_parts.append(content)

    return "".join(text_parts)
