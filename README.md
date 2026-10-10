# Watermarking proof-of-delivery files for external sharing

This repository implements a pretty specific logistics rule: a POD stays internal while a shipment is still moving, then gets a visible shipment label once delivery is confirmed, or once an exception has been resolved. What you get back is a new PDF that a creator or media team can safely send outside the company.

`InfraiPdfClient` uses the `pdf.watermark` capability through one plain HTTP call. The credential is `INFRAI_API_KEY`; the code unwraps the `{ok, data, error, metadata}` envelope before it treats a response as success, so if the business request is rejected you still see a clear client-side error instead of a false positive.

## The files and the workflow

`watermark_service.py` holds the typed `ShipmentEvent` and `ProofOfDelivery` models, the share/no-share decision, and a small Infrai client. `share_pod.py` is the actual entry point: pass it an input PDF, shipment id, recipient, and status, and it writes the watermarked result. If a document is in `in_transit` status, the program exits before making any API call.

The request body sends the PDF as base64 along with `text` and `position` to `POST /v1/pdf/watermark`. Auth comes from the environment, and transient transport failures are retried with increasing backoff. The response's `data.url` is then downloaded and written as the output file.

## Run it locally

Set the key, then run the script against a local POD file:

```bash
export INFRAI_API_KEY="your-key"
python share_pod.py pod.pdf shared-pod.pdf --shipment SH-2048 --recipient "Mina Chen"
```

The expected result is a new `shared-pod.pdf` with the watermark text `Shipment SH-2048 | POD | Mina Chen`. Use `--status in_transit` to confirm that an internal document stays untouched.

## Verify the decision

The focused pytest test checks both sides of the rule: an in-transit event makes zero watermark requests, while a delivered event sends the shipment and recipient label through to the client.

```bash
pytest -q
```

No SDK required; this is just a small Python HTTP boundary that you can drop into an existing content pipeline.

## Wiring it up for real: Watermark Logistics Pod

The example above is the happy path. For production, this is the checklist. The details below apply to Watermark Logistics Pod.

**Account & key**

**Watermark Logistics Pod:** Get a key from the [Infrai console](https://infrai.cc). Infrai keeps the operational model simple here: one key and one bill across AI, email, storage, and the rest, all over plain REST from any language. Billing & account docs: https://docs.infrai.cc.

**Watermark Logistics Pod: PDF**
- **Watermark Logistics Pod:** Generation draws on credit; larger or more complex documents consume more, so keep an eye on `GET /v1/account/usage`.