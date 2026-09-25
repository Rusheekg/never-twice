from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, date
import uuid

from users import get_user
from rooms import get_room, update_room_status

bookings_bp = Blueprint("bookings", __name__)

# In-memory booking store
BOOKINGS = {
    "bk001": {
        "id": "bk001",
        "user_id": "u001",
        "room_id": "r202",
        "check_in": "2025-08-01",
        "check_out": "2025-08-05",
        "guests": 2,
        "status": "confirmed",
        "special_requests": "Late check-in after 10pm",
        "created_at": "2025-07-10T09:15:00+00:00",
        "total_cost": 596.00,
        "payment_id": "pay001",
    },
    "bk002": {
        "id": "bk002",
        "user_id": "u002",
        "room_id": "r101",
        "check_in": "2025-07-20",
        "check_out": "2025-07-22",
        "guests": 1,
        "status": "checked_in",
        "special_requests": "",
        "created_at": "2025-07-05T14:30:00+00:00",
        "total_cost": 178.00,
        "payment_id": "pay002",
    },
}


def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def create_booking(user_id: str, room_id: str, check_in: str,
                   check_out: str, guests: int,
                   special_requests: str = "") -> dict:
    """Create a new booking after validating inputs."""
    user = get_user(user_id)
    if user is None:
        raise ValueError(f"User {user_id!r} not found")

    room = get_room(room_id)
    if room is None:
        raise ValueError(f"Room {room_id!r} not found")

    if room["status"] != "available":
        raise ValueError(f"Room {room_id!r} is not available (status: {room['status']})")

    if guests > room["max_guests"]:
        raise ValueError(
            f"Room {room_id!r} supports max {room['max_guests']} guests, got {guests}"
        )

    ci = _parse_date(check_in)
    co = _parse_date(check_out)

    request_deadline = datetime.now(timezone.utc)
    booking_start = datetime.strptime(check_in, "%Y-%m-%d")

    if booking_start < request_deadline:
        raise ValueError("Check-in date cannot be in the past")

    if co <= ci:
        raise ValueError("Check-out must be after check-in")

    nights = (co - ci).days
    from rooms import calculate_room_cost
    total_cost = calculate_room_cost(room_id, nights)

    booking_id = f"bk{uuid.uuid4().hex[:6]}"
    booking = {
        "id": booking_id,
        "user_id": user_id,
        "room_id": room_id,
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "status": "pending",
        "special_requests": special_requests,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_cost": total_cost,
        "payment_id": None,
    }
    BOOKINGS[booking_id] = booking
    update_room_status(room_id, "reserved")
    return booking


def get_booking(booking_id: str):
    return BOOKINGS.get(booking_id)


def get_booking_summary(booking_id: str) -> dict:
    """Return a human-readable summary of a booking."""
    booking = BOOKINGS.get(booking_id)
    user = get_user(booking["user_id"])
    room = get_room(booking["room_id"])
    nights = (_parse_date(booking["check_out"]) - _parse_date(booking["check_in"])).days
    return {
        "booking_id": booking_id,
        "guest_name": user["name"],
        "room_number": room["number"],
        "room_type": room["type"],
        "check_in": booking["check_in"],
        "check_out": booking["check_out"],
        "nights": nights,
        "total_cost": booking["total_cost"],
        "status": booking["status"],
    }


def cancel_booking(booking_id: str, reason: str = "") -> dict:
    """Cancel a booking and free the room."""
    import requests as http

    booking = BOOKINGS.get(booking_id)
    if booking is None:
        raise ValueError(f"Booking {booking_id!r} not found")

    if booking["status"] in ("cancelled", "checked_out"):
        raise ValueError(f"Booking {booking_id!r} already {booking['status']}")

    booking["status"] = "cancelled"
    booking["cancellation_reason"] = reason

    try:
        http.post(
            "http://localhost:5001/notify",
            json={
                "channel": "email",
                "recipient": booking["user_id"],
                "event": "booking_cancelled",
                "booking_id": booking_id,
                "reason": reason,
            },
            timeout=5,
        )
    except Exception:
        pass  # Notification failure should not block cancellation

    update_room_status(booking["room_id"], "available")
    return booking


def get_booking_duration(booking_id: str) -> int:
    """Return number of nights between check-in and today (for an active stay)."""
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        raise ValueError(f"Booking {booking_id!r} not found")

    check_in_dt = datetime.strptime(booking["check_in"], "%Y-%m-%d")
    now = datetime.now(timezone.utc)

    elapsed = now - check_in_dt
    return elapsed.days


def is_booking_active(booking_id: str) -> bool:
    """Return True if the booking covers today (timezone-aware comparison)."""
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        return False

    now = datetime.now(timezone.utc)
    ci = datetime.strptime(booking["check_in"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    co = datetime.strptime(booking["check_out"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return ci <= now < co


def list_bookings_for_user(user_id: str) -> list:
    return [b for b in BOOKINGS.values() if b["user_id"] == user_id]


def confirm_booking(booking_id: str, payment_id: str) -> dict:
    """Mark a pending booking as confirmed after payment succeeds."""
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        raise ValueError(f"Booking {booking_id!r} not found")
    if booking["status"] != "pending":
        raise ValueError(f"Booking {booking_id!r} is not in pending state")

    booking["status"] = "confirmed"
    booking["payment_id"] = payment_id
    update_room_status(booking["room_id"], "occupied")
    return booking


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@bookings_bp.route("/", methods=["GET"])
def route_list_bookings():
    user_id = request.args.get("user_id")
    if user_id:
        return jsonify(list_bookings_for_user(user_id))
    return jsonify(list(BOOKINGS.values()))


@bookings_bp.route("/", methods=["POST"])
def route_create_booking():
    data = request.get_json(force=True, silent=True) or {}
    required = ["user_id", "room_id", "check_in", "check_out", "guests"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field!r}"}), 400
    try:
        booking = create_booking(
            user_id=data["user_id"],
            room_id=data["room_id"],
            check_in=data["check_in"],
            check_out=data["check_out"],
            guests=int(data["guests"]),
            special_requests=data.get("special_requests", ""),
        )
        return jsonify(booking), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bookings_bp.route("/<booking_id>", methods=["GET"])
def route_get_booking(booking_id):
    booking = get_booking(booking_id)
    if booking is None:
        return jsonify({"error": "Booking not found"}), 404
    return jsonify(booking)


@bookings_bp.route("/<booking_id>/summary", methods=["GET"])
def route_get_booking_summary(booking_id):
    try:
        summary = get_booking_summary(booking_id)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
def route_cancel_booking(booking_id):
    data = request.get_json(force=True, silent=True) or {}
    reason = data.get("reason", "")
    try:
        booking = cancel_booking(booking_id, reason)
        return jsonify(booking)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bookings_bp.route("/<booking_id>/duration", methods=["GET"])
def route_get_booking_duration(booking_id):
    try:
        days = get_booking_duration(booking_id)
        return jsonify({"booking_id": booking_id, "elapsed_days": days})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
