import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import mkstemp
from uuid import UUID

import anyio
import fitz
from fastapi import HTTPException, Request
from gulfdocs_document_intelligence.adapters.local import LocalFileStorage
from gulfdocs_persistence.models import DocumentUpload


def upload_capability(secret: str, document_id: UUID, expires_at: datetime) -> str:
    payload = f"{document_id}:{int(expires_at.timestamp())}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def capability_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_upload_capability(secret: str, upload: DocumentUpload, token: str) -> None:
    expected = upload_capability(secret, upload.document_id, upload.expires_at)
    if not hmac.compare_digest(expected, token) or not hmac.compare_digest(
        upload.upload_token_hash, capability_hash(token)
    ):
        raise HTTPException(status_code=403, detail="Invalid upload capability")
    if upload.status != "pending":
        raise HTTPException(status_code=409, detail="Upload is no longer pending")
    if upload.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail="Upload capability has expired")


async def store_bounded_pdf(
    request: Request,
    *,
    upload: DocumentUpload,
    storage: LocalFileStorage,
    max_size_bytes: int,
) -> None:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds the upload size limit")
    if request.headers.get("content-type", "").split(";", 1)[0] != "application/pdf":
        raise HTTPException(status_code=415, detail="Only application/pdf uploads are accepted")
    total = 0
    descriptor, temporary_name = mkstemp(suffix=".pdf")
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        async with await anyio.open_file(temporary_path, "wb") as temporary:
            async for chunk in request.stream():
                total += len(chunk)
                if total > max_size_bytes or total > upload.expected_size_bytes:
                    raise HTTPException(status_code=413, detail="PDF exceeds the declared size")
                await temporary.write(chunk)
            if total != upload.expected_size_bytes:
                raise HTTPException(
                    status_code=400, detail="Uploaded size does not match declaration"
                )
            await temporary.flush()
        await storage.put_at(upload.object_key, temporary_path)
    finally:
        await anyio.Path(temporary_path).unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class InspectedPdf:
    size_bytes: int
    sha256: str
    page_count: int


def inspect_pdf(path: Path, *, max_size_bytes: int, max_pages: int) -> InspectedPdf:
    size_bytes = path.stat().st_size
    if size_bytes <= 0 or size_bytes > max_size_bytes:
        raise HTTPException(status_code=422, detail="PDF size is invalid")
    content = path.read_bytes()
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File signature is not a PDF")
    try:
        with fitz.open(path) as pdf:
            if pdf.needs_pass:
                raise HTTPException(status_code=422, detail="Encrypted PDFs are not supported")
            page_count = pdf.page_count
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="PDF is damaged or unreadable") from exc
    if page_count < 1 or page_count > max_pages:
        raise HTTPException(status_code=422, detail=f"PDF must contain 1 to {max_pages} pages")
    return InspectedPdf(
        size_bytes=size_bytes,
        sha256=hashlib.sha256(content).hexdigest(),
        page_count=page_count,
    )
