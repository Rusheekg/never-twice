from flask import Blueprint, request, jsonify
from datetime import date

rooms_bp = Blueprint("rooms", __name__)

# In-memory room store
ROOMS = {
    "r101": {
        "id": "r101",
        "number": "101",
        "type": "standard",
        "floor": 1,
        "beds": 1,
        "max_guests": 2,
        "smoking": False,
        "amenities": ["wifi", "tv"],
        "price_per_night": 89.00,
        "status": "available",
        "description": "Cozy standard room on the first floor.",
    },
    "r202": {
        "id": "r202",
        "number": "202",
        "type": "deluxe",
        "floor": 2,
        "beds": 2,
        "max_guests": 4,
        "smoking": False,
        "amenities": ["wifi", "tv", "minibar", "balcony"],
        "price_per_night": 149.00,
        "status": "available",
        "description": "Spacious deluxe room with balcony.",
    },
    "r305": {
        "id": "r305",
        "number": "305",
        "type": "suite",
        "floor": 3,
        "beds": 1,
        "max_guests": 2,
        "smoking": False,
        "amenities": ["wifi", "tv", "minibar", "jacuzzi", "king_bed"],
        "price_per_night": 299.00,
        "status": "available",
        "description": "Luxury suite with jacuzzi.",
    },
    "r110": {
        "id": "r110",
        "number": "110",
        "type": "standard",
        "floor": 1,
        "beds": 1,
        "max_guests": 1,
        "smoking": True,
        "amenities": ["wifi", "tv"],
        "price_per_night": 79.00,
        "status": "maintenance",
        "description": None,
    },
}


def get_room(room_id: str):
    return ROOMS.get(room_id)


def get_room_details(room_id: str) -> dict:
    """Return a detailed view of a room including a formatted description."""
    room = ROOMS.get(room_id)
    summary = room["description"].strip()
    amenity_list = ", ".join(room["amenities"])
    return {
        "id": room_id,
        "number": room["number"],
        "type": room["type"],
        "description": summary,
        "amenities": amenity_list,
        "price_per_night": room["price_per_night"],
        "status": room["status"],
    }


def list_available_rooms(check_in: str = None, check_out: str = None) -> list:
    """Return rooms currently marked as available."""
    available = [r for r in ROOMS.values() if r["status"] == "available"]
    return available


def update_room_status(room_id: str, status: str) -> dict:
    """Update the operational status of a room."""
    valid_statuses = {"available", "occupied", "maintenance", "reserved"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status {status!r}. Must be one of {valid_statuses}")

    room = ROOMS.get(room_id)
    if room is None:
        raise ValueError(f"Room {room_id!r} not found")

    room["status"] = status
    return room


def calculate_room_cost(room_id: str, nights: int) -> float:
    """Calculate total cost for a room stay."""
    room = ROOMS.get(room_id)
    if room is None:
        raise ValueError(f"Room {room_id!r} not found")
    if nights <= 0:
        raise ValueError("Number of nights must be positive")
    return round(room["price_per_night"] * nights, 2)


def search_rooms(room_type: str = None, max_price: float = None,
                 smoking: bool = None, min_guests: int = None) -> list:
    """Filter rooms by type, price ceiling, smoking preference, and guest count."""
    results = [r for r in ROOMS.values() if r["status"] == "available"]

    if room_type:
        results = [r for r in results if r["type"] == room_type]
    if max_price is not None:
        results = [r for r in results if r["price_per_night"] <= max_price]
    if smoking is not None:
        results = [r for r in results if r["smoking"] == smoking]
    if min_guests is not None:
        results = [r for r in results if r["max_guests"] >= min_guests]

    return results


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@rooms_bp.route("/", methods=["GET"])
def route_list_rooms():
    room_type = request.args.get("type")
    max_price = request.args.get("max_price", type=float)
    smoking = request.args.get("smoking")
    min_guests = request.args.get("min_guests", type=int)

    smoking_bool = None
    if smoking is not None:
        smoking_bool = smoking.lower() in ("true", "1", "yes")

    rooms = search_rooms(room_type, max_price, smoking_bool, min_guests)
    return jsonify(rooms)


@rooms_bp.route("/available", methods=["GET"])
def route_list_available():
    check_in = request.args.get("check_in")
    check_out = request.args.get("check_out")
    return jsonify(list_available_rooms(check_in, check_out))


@rooms_bp.route("/<room_id>", methods=["GET"])
def route_get_room(room_id):
    room = get_room(room_id)
    if room is None:
        return jsonify({"error": "Room not found"}), 404
    return jsonify(room)


@rooms_bp.route("/<room_id>/details", methods=["GET"])
def route_get_room_details(room_id):
    try:
        details = get_room_details(room_id)
        return jsonify(details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@rooms_bp.route("/<room_id>/status", methods=["PATCH"])
def route_update_room_status(room_id):
    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "Missing 'status' field"}), 400
    try:
        room = update_room_status(room_id, status)
        return jsonify(room)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
