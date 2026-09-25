from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import uuid
import requests as http

notifications_bp = Blueprint("notifications", __name__)

MOCK_NOTIFY_URL = "http://localhost:5001/notify"

# In-memory notification log
NOTIFICATIONS = {}


def send_email_notification(user_id: str, subject: str, body: str) -> dict:
    """Send an email notification via the mock gateway."""
    payload = {
        "channel": "email",
        "recipient": user_id,
        "subject": subject,
        "body": body,
    }

    try:
        response = http.post(MOCK_NOTIFY_URL, json=payload, timeout=5)
        gateway_data = response.json()
    except http.exceptions.Timeout:
        raise RuntimeError("Notification service timed out")
    except http.exceptions.RequestException as exc:
        raise RuntimeError(f"Notification service unreachable: {exc}")

    if response.status_code != 200 or gateway_data.get("status") != "sent":
        raise RuntimeError(
            f"Notification failed: {gateway_data.get('message', 'unknown error')}"
        )

    notification_id = f"ntf{uuid.uuid4().hex[:6]}"
    record = {
        "id": notification_id,
        "user_id": user_id,
        "channel": "email",
        "subject": subject,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "gateway_ref": gateway_data.get("ref"),
    }
    NOTIFICATIONS[notification_id] = record
    return record


def send_sms_notification(user_id: str, message: str) -> dict:
    """Send an SMS notification via the mock gateway."""
    payload = {
        "channel": "sms",
        "recipient": user_id,
        "message": message,
    }

    response = http.post(MOCK_NOTIFY_URL, json=payload)
    gateway_data = response.json()

    if response.status_code != 200 or gateway_data.get("status") != "sent":
        raise RuntimeError(
            f"SMS failed: {gateway_data.get('message', 'unknown error')}"
        )

    notification_id = f"ntf{uuid.uuid4().hex[:6]}"
    record = {
        "id": notification_id,
        "user_id": user_id,
        "channel": "sms",
        "message": message,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "gateway_ref": gateway_data.get("ref"),
    }
    NOTIFICATIONS[notification_id] = record
    return record


def notify_booking_confirmed(user_id: str, booking_id: str,
                              room_number: str, check_in: str) -> dict:
    """Convenience wrapper: email + SMS on booking confirmation."""
    subject = f"Booking {booking_id} Confirmed"
    body = (
        f"Your booking ({booking_id}) for room {room_number} "
        f"is confirmed. Check-in: {check_in}."
    )
    return send_email_notification(user_id, subject, body)


def notify_payment_received(user_id: str, booking_id: str, amount: float) -> dict:
    """Send payment receipt via SMS."""
    message = (
        f"Payment of ${amount:.2f} received for booking {booking_id}. "
        "Thank you for choosing Grand Hotel."
    )
    return send_sms_notification(user_id, message)


def get_notification_log(user_id: str = None) -> list:
    """Return all notifications, optionally filtered by user."""
    if user_id:
        return [n for n in NOTIFICATIONS.values() if n["user_id"] == user_id]
    return list(NOTIFICATIONS.values())


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@notifications_bp.route("/", methods=["GET"])
def route_list_notifications():
    user_id = request.args.get("user_id")
    return jsonify(get_notification_log(user_id))


@notifications_bp.route("/email", methods=["POST"])
def route_send_email():
    data = request.get_json(force=True, silent=True) or {}
    required = ["user_id", "subject", "body"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field!r}"}), 400
    try:
        record = send_email_notification(data["user_id"], data["subject"], data["body"])
        return jsonify(record), 201
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502


@notifications_bp.route("/sms", methods=["POST"])
def route_send_sms():
    data = request.get_json(force=True, silent=True) or {}
    required = ["user_id", "message"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field!r}"}), 400
    try:
        record = send_sms_notification(data["user_id"], data["message"])
        return jsonify(record), 201
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502


@notifications_bp.route("/<notification_id>", methods=["GET"])
def route_get_notification(notification_id):
    record = NOTIFICATIONS.get(notification_id)
    if record is None:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify(record)
