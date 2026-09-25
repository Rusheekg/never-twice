"""
Mock external services — payment gateway and notification gateway.

Run this on port 5001 before starting the main API:
    python mock_services.py

Failure and latency simulation
-------------------------------
All endpoints accept query parameters:
  - ?fail=1        Force a failure response
  - ?slow=1        Add a 3-second delay before responding
  - ?slow=5        Add a 5-second delay (use any positive int)

Random failures can also be toggled:
  - ?random_fail=1  10% chance of returning a failure response

These parameters let you test timeout handling, retry logic, and error
recovery in the main API without modifying any production code.
"""

import time
import random
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)


def _should_fail() -> bool:
    if request.args.get("fail") in ("1", "true", "yes"):
        return True
    if request.args.get("random_fail") in ("1", "true", "yes"):
        return random.random() < 0.10
    return False


def _apply_delay() -> None:
    slow = request.args.get("slow")
    if slow:
        try:
            seconds = int(slow)
            if seconds > 0:
                time.sleep(seconds)
        except ValueError:
            time.sleep(3)


# ---------------------------------------------------------------------------
# Payment gateway endpoints
# ---------------------------------------------------------------------------

@app.route("/payment/charge", methods=["POST"])
def charge():
    _apply_delay()

    data = request.get_json(force=True, silent=True) or {}
    amount = data.get("amount", 0)
    method = data.get("method", "unknown")

    if _should_fail():
        return jsonify({
            "status": "error",
            "message": "Card declined by issuing bank",
            "code": "card_declined",
        }), 402

    if not data.get("booking_id") or not data.get("user_id"):
        return jsonify({
            "status": "error",
            "message": "Missing booking_id or user_id",
            "code": "invalid_request",
        }), 400

    if amount <= 0:
        return jsonify({
            "status": "error",
            "message": "Amount must be greater than zero",
            "code": "invalid_amount",
        }), 400

    transaction_id = f"gw_{uuid.uuid4().hex[:8]}"
    return jsonify({
        "status": "success",
        "transaction_id": transaction_id,
        "amount": amount,
        "method": method,
        "currency": data.get("currency", "USD"),
        "message": "Payment authorised",
    })


@app.route("/payment/refund", methods=["POST"])
def refund():
    _apply_delay()

    data = request.get_json(force=True, silent=True) or {}

    if _should_fail():
        return jsonify({
            "status": "error",
            "message": "Refund window expired",
            "code": "refund_expired",
        }), 422

    if not data.get("transaction_id"):
        return jsonify({
            "status": "error",
            "message": "Missing transaction_id",
            "code": "invalid_request",
        }), 400

    refund_ref = f"ref_{uuid.uuid4().hex[:8]}"
    return jsonify({
        "status": "success",
        "refund_ref": refund_ref,
        "original_transaction": data.get("transaction_id"),
        "amount": data.get("amount"),
        "message": "Refund processed",
    })


# ---------------------------------------------------------------------------
# Notification gateway endpoint
# ---------------------------------------------------------------------------

@app.route("/notify", methods=["POST"])
def notify():
    _apply_delay()

    data = request.get_json(force=True, silent=True) or {}
    channel = data.get("channel", "unknown")
    recipient = data.get("recipient")

    if _should_fail():
        return jsonify({
            "status": "error",
            "message": f"Delivery failed for channel {channel!r}",
            "code": "delivery_failure",
        }), 503

    if not recipient:
        return jsonify({
            "status": "error",
            "message": "Missing recipient",
            "code": "invalid_request",
        }), 400

    valid_channels = {"email", "sms"}
    if channel not in valid_channels:
        return jsonify({
            "status": "error",
            "message": f"Unknown channel {channel!r}",
            "code": "invalid_channel",
        }), 400

    notification_ref = f"ntf_{uuid.uuid4().hex[:8]}"
    return jsonify({
        "status": "sent",
        "ref": notification_ref,
        "channel": channel,
        "recipient": recipient,
        "message": f"Notification queued via {channel}",
    })


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "mock-external-services"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
