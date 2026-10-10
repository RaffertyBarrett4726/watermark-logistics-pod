import json
from urllib.error import HTTPError

import pytest

from watermark_service import InfraiPdfClient, ProofOfDelivery, ShipmentEvent, prepare_external_share


class RecordingClient:
    def __init__(self):
        self.calls = []

    def watermark(self, pdf: bytes, text: str):
        self.calls.append((pdf, text))
        return b"watermarked"


def test_in_transit_pod_is_not_shared():
    client = RecordingClient()
    event = ShipmentEvent("S-17", "in_transit", "Mina")
    proof = ProofOfDelivery("pod.pdf", b"pdf-bytes")
    assert prepare_external_share(event, proof, client) is None
    assert client.calls == []


def test_delivered_pod_gets_recipient_label():
    client = RecordingClient()
    event = ShipmentEvent("S-17", "delivered", "Mina")
    proof = ProofOfDelivery("pod.pdf", b"pdf-bytes")
    assert prepare_external_share(event, proof, client) == b"watermarked"
    assert client.calls == [(b"pdf-bytes", "Shipment S-17 | POD | Mina")]


class FakeResponse:
    status = 200

    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.content


def test_watermark_downloads_response_url():
    calls = []

    def opener(req):
        calls.append(req)
        if len(calls) == 1:
            return FakeResponse(json.dumps({"ok": True, "data": {"url": "https://example.com/output.pdf"}}).encode())
        return FakeResponse(b"%PDF-watermarked")

    assert InfraiPdfClient("test-key", opener).watermark(b"%PDF-original", "label") == b"%PDF-watermarked"
    assert len(calls) == 2
    assert calls[1].full_url == "https://example.com/output.pdf"


def test_watermark_does_not_retry_http_errors():
    calls = []

    def opener(req):
        calls.append(req)
        raise HTTPError(req.full_url, 503, "unavailable", {}, None)

    with pytest.raises(HTTPError):
        InfraiPdfClient("test-key", opener).watermark(b"%PDF-original", "label")
    assert len(calls) == 1
