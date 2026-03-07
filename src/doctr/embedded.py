from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader


SUPPORTED_EMBEDDED_EXTS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xlsm",
    ".md",
    ".markdown",
    ".txt",
    ".msg",
}


@dataclass(slots=True)
class ExtractedEmbeddedFile:
    name: str
    path: str
    parent_path: str
    kind: str


def _safe_name(name: str) -> str:
    return os.path.basename(name.replace("\\", "/")) or "embedded.bin"


def extract_embedded_files(path: str, temp_dir_path: str) -> list[ExtractedEmbeddedFile]:
    suffix = Path(path).suffix.lower()
    if suffix in {".docx", ".xlsx", ".xlsm", ".pptx"}:
        return _extract_from_zip_container(path, temp_dir_path)
    if suffix == ".pdf":
        return _extract_from_pdf_attachments(path, temp_dir_path)
    return []


def _extract_from_zip_container(
    path: str, temp_dir_path: str
) -> list[ExtractedEmbeddedFile]:
    out: list[ExtractedEmbeddedFile] = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            candidates = [
                n
                for n in names
                if "/embeddings/" in n.lower() or n.lower().startswith("embeddings/")
            ]
            for name in candidates:
                ext = Path(name).suffix.lower()
                if ext not in SUPPORTED_EMBEDDED_EXTS:
                    continue
                data = zf.read(name)
                target = os.path.join(temp_dir_path, _safe_name(name))
                with open(target, "wb") as f:
                    f.write(data)
                out.append(
                    ExtractedEmbeddedFile(
                        name=_safe_name(name),
                        path=target,
                        parent_path=path,
                        kind="zip_embedding",
                    )
                )
    except Exception:
        return out
    return out


def _extract_from_pdf_attachments(
    path: str, temp_dir_path: str
) -> list[ExtractedEmbeddedFile]:
    out: list[ExtractedEmbeddedFile] = []
    try:
        reader = PdfReader(path)
    except Exception:
        return out

    attachments: dict[str, Any] = {}
    try:
        attachments = reader.attachments  # pypdf>=4
    except Exception:
        return out

    for name, values in attachments.items():
        ext = Path(name).suffix.lower()
        if ext not in SUPPORTED_EMBEDDED_EXTS:
            continue
        blobs = values if isinstance(values, list) else [values]
        for i, blob in enumerate(blobs, start=1):
            if not isinstance(blob, (bytes, bytearray)):
                continue
            base = _safe_name(name)
            if len(blobs) > 1:
                stem, e = os.path.splitext(base)
                base = f"{stem}_{i}{e}"
            target = os.path.join(temp_dir_path, base)
            with open(target, "wb") as f:
                f.write(blob)
            out.append(
                ExtractedEmbeddedFile(
                    name=base,
                    path=target,
                    parent_path=path,
                    kind="pdf_attachment",
                )
            )
    return out
