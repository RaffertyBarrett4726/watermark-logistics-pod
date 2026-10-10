"""Runnable example: watermark one proof-of-delivery PDF."""
from pathlib import Path
import argparse

from watermark_service import InfraiPdfClient, ProofOfDelivery, ShipmentEvent, prepare_external_share


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("output_pdf", type=Path)
    parser.add_argument("--shipment", required=True)
    parser.add_argument("--recipient", required=True)
    parser.add_argument("--status", choices=["delivered", "exception_resolved", "in_transit"], default="delivered")
    args = parser.parse_args()
    event = ShipmentEvent(args.shipment, args.status, args.recipient)
    proof = ProofOfDelivery(args.input_pdf.name, args.input_pdf.read_bytes())
    output = prepare_external_share(event, proof, InfraiPdfClient())
    if output is None:
        raise SystemExit("document remains internal until the shipment is ready")
    args.output_pdf.write_bytes(output)
    print(f"wrote watermarked POD to {args.output_pdf}")


if __name__ == "__main__":
    main()

