from __future__ import annotations

from typing import Protocol

from .models import DocumentIndex


class IndexEnricher(Protocol):
    def __call__(self, index: DocumentIndex) -> DocumentIndex:
        ...

