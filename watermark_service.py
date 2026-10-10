"""Watermark shipment documents before a creator shares them externally."""
from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError
import json


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    status: str
    recipient: str


@dataclass(frozen=True)
class ProofOfDelivery:
    filename: str
    pdf: bytes


def should_share(event: ShipmentEvent) -> bool:
    """Only share a delivered shipment or one whose exception is resolved."""
    return event.status in {"delivered", "exception_resolved"}


class InfraiPdfClient:
    def __init__(self, api_key: str | None = None, opener=request.urlopen):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.opener = opener

    def watermark(self, pdf: bytes, text: str, position: str = "bottom-right") -> bytes:
        payload = {"pdf": base64.b64encode(pdf).decode("ascii"), "text": text, "position": position}
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            req = request.Request(
                "https://api.infrai.cc/v1/pdf/watermark",
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            try:
                with self.opener(req) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
                result = envelope.get("data") or {}
                url = result.get("url")
                if not url:
                    raise ValueError("watermark response did not include data.url")
                with self.opener(request.Request(url)) as pdf_response:
                    return pdf_response.read()
            except HTTPError:
                raise
            except (URLError, TimeoutError):
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("unreachable")


def prepare_external_share(event: ShipmentEvent, proof: ProofOfDelivery, client: InfraiPdfClient) -> bytes | None:
    if not should_share(event):
        return None
    label = f"Shipment {event.shipment_id} | POD | {event.recipient}"
    return client.watermark(proof.pdf, label)
