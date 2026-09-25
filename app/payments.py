from flask import Blueprint, request, jsonify
import uuid
import requests as http

payments_bp = Blueprint("payments", __name__)

MOCK_PAYMENT_URL = "http://localhost:5001/payment/charge"
MOCK_REFUND_URL = "http://localhost:5001/payment/refund"

# In-memory payment store
PAYMENTS = {
    "pay001": {
        "id": "pay001",
        "booking_id": "bk001",
        "user_id": "u001",
        "amount": 596.00,
        "currency": "USD",
        "status": "completed",
        "method": "credit_card",
        "gateway_ref": "gw_abc123",
        "created_at": "2025-07-10T09:16:00+00:00",
        "refunded": False,
    },
    "pay002": {
        "id": "pay002",
        "booking_id": "bk002",
        "user_id": "u002",
        "amount": 178.00,
        "currency": "USD",
        "status": "completed",
        "method": "debit_card",
        "gateway_ref": "gw_def456",
        "created_at": "2025-07-05T14:31:00+00:00",
        "refunded": False,
    },
}


def process_payment(booking_id: str, user_id: str, amount: float,
                    method: str = "credit_card") -> dict:
    """Charge the customer via the external payment gateway."""
    payload = {
        "booking_id": booking_id,
        "user_id": user_id,
        "amount": amount,
        "method": method,
        "currency": "USD",
    }

    response = http.post(MOCK_PAYMENT_URL, json=payload)
    gateway_data = response.json()

    if response.status_code != 200 or gateway_data.get("status") != "success":
        raise RuntimeError(
            f"Payment gateway error: {gateway_data.get('message', 'unknown error')}"
        )

    payment_id = f"pay{uuid.uuid4().hex[:6]}"
    payment = {
        "id": payment_id,
        "booking_id": booking_id,
        "user_id": user_id,
        "amount": amount,
        "currency": "USD",
        "status": "completed",
        "method": method,
        "gateway_ref": gateway_data.get("transaction_id"),
        "created_at": None,
        "refunded": False,
    }
    from datetime import datetime, timezone
    payment["created_at"] = datetime.now(timezone.utc).isoformat()
    PAYMENTS[payment_id] = payment
    return payment


def get_payment(payment_id: str):
    return PAYMENTS.get(payment_id)


def get_payment_status(booking_id: str) -> dict:
    """Return the payment record for a given booking."""
    for payment in PAYMENTS.values():
        if payment["booking_id"] == booking_id:
            return {
                "payment_id": payment["id"],
                "status": payment["status"],
                "amount": payment["amount"],
                "refunded": payment["refunded"],
            }
    return {"payment_id": None, "status": "not_found", "amount": 0, "refunded": False}


def refund_payment(payment_id: str, reason: str = "") -> dict:
    """Request a refund from the gateway for a completed payment."""
    payment = PAYMENTS.get(payment_id)
    if payment is None:
        raise ValueError(f"Payment {payment_id!r} not found")
    if payment["status"] != "completed":
        raise ValueError(f"Payment {payment_id!r} is not in a refundable state")
    if payment["refunded"]:
        raise ValueError(f"Payment {payment_id!r} has already been refunded")

    payload = {
        "transaction_id": payment["gateway_ref"],
        "amount": payment["amount"],
        "reason": reason,
    }

    try:
        response = http.post(MOCK_REFUND_URL, json=payload, timeout=8)
        gateway_data = response.json()
    except http.exceptions.Timeout:
        raise RuntimeError("Refund gateway timed out — please retry")
    except http.exceptions.RequestException as exc:
        raise RuntimeError(f"Refund gateway unreachable: {exc}")

    if response.status_code != 200 or gateway_data.get("status") != "success":
        raise RuntimeError(
            f"Refund failed: {gateway_data.get('message', 'unknown error')}"
        )

    payment["refunded"] = True
    payment["status"] = "refunded"
    return payment


def list_payments_for_user(user_id: str) -> list:
    return [p for p in PAYMENTS.values() if p["user_id"] == user_id]


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@payments_bp.route("/", methods=["GET"])
def route_list_payments():
    user_id = request.args.get("user_id")
    if user_id:
        return jsonify(list_payments_for_user(user_id))
    return jsonify(list(PAYMENTS.values()))


@payments_bp.route("/<payment_id>", methods=["GET"])
def route_get_payment(payment_id):
    payment = get_payment(payment_id)
    if payment is None:
        return jsonify({"error": "Payment not found"}), 404
    return jsonify(payment)


@payments_bp.route("/charge", methods=["POST"])
def route_process_payment():
    data = request.get_json(force=True, silent=True) or {}
    required = ["booking_id", "user_id", "amount"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field!r}"}), 400
    try:
        payment = process_payment(
            booking_id=data["booking_id"],
            user_id=data["user_id"],
            amount=float(data["amount"]),
            method=data.get("method", "credit_card"),
        )
        return jsonify(payment), 201
    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 400


@payments_bp.route("/<payment_id>/refund", methods=["POST"])
def route_refund_payment(payment_id):
    data = request.get_json(force=True, silent=True) or {}
    reason = data.get("reason", "")
    try:
        payment = refund_payment(payment_id, reason)
        return jsonify(payment)
    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 400


@payments_bp.route("/status/<booking_id>", methods=["GET"])
def route_get_payment_status(booking_id):
    return jsonify(get_payment_status(booking_id))
