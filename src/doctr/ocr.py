from __future__ import annotations

import time
from typing import Any


class PageIndexOCRProvider:
    """
    Adapter for PageIndex OCR-style APIs.
    Endpoint templates are configurable because deployments may vary.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.pageindex.ai",
        submit_endpoint: str = "/ocr/documents",
        status_endpoint_template: str = "/ocr/documents/{doc_id}",
        timeout_seconds: int = 900,
        poll_interval_seconds: int = 2,
        result_format: str = "node",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.submit_endpoint = submit_endpoint
        self.status_endpoint_template = status_endpoint_template
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.result_format = result_format

    def _requests(self):
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Install OCR deps first: pip install 'doctr[ocr]'") from exc
        return requests

    def run(self, path: str) -> dict[str, Any]:
        requests = self._requests()
        headers = {"Authorization": f"Bearer {self.api_key}"}

        with open(path, "rb") as f:
            submit_resp = requests.post(
                f"{self.base_url}{self.submit_endpoint}",
                headers=headers,
                files={"file": f},
                data={"format": self.result_format},
                timeout=120,
            )
        submit_resp.raise_for_status()
        submit_payload = submit_resp.json()
        doc_id = submit_payload.get("doc_id") or submit_payload.get("id")
        if not doc_id:
            raise RuntimeError(f"Could not find doc_id in OCR submit response: {submit_payload}")

        deadline = time.time() + self.timeout_seconds
        status_url = f"{self.base_url}{self.status_endpoint_template.format(doc_id=doc_id)}"
        while time.time() < deadline:
            status_resp = requests.get(
                status_url,
                headers=headers,
                params={"format": self.result_format},
                timeout=60,
            )
            status_resp.raise_for_status()
            status_payload = status_resp.json()
            status = (status_payload.get("status") or "").lower()
            if status in {"completed", "succeeded", "done"}:
                return status_payload
            if status in {"failed", "error"}:
                raise RuntimeError(f"OCR failed: {status_payload}")
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError("Timed out waiting for OCR job to complete")

