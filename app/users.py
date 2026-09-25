from flask import Blueprint, request, jsonify

users_bp = Blueprint("users", __name__)

# In-memory user store
USERS = {
    "u001": {
        "id": "u001",
        "name": "Alice Nguyen",
        "email": "alice@example.com",
        "phone": "+1-555-0101",
        "loyalty_tier": "gold",
        "preferences": {"smoking": False, "floor": "high"},
        "billing_address": "12 Maple St, Springfield",
    },
    "u002": {
        "id": "u002",
        "name": "Bob Patel",
        "email": "bob@example.com",
        "phone": "+1-555-0202",
        "loyalty_tier": "silver",
        "preferences": {"smoking": False, "floor": "low"},
        "billing_address": "9 Oak Ave, Shelbyville",
    },
    "u003": {
        "id": "u003",
        "name": "Carol Smith",
        "email": "carol@example.com",
        "phone": "+1-555-0303",
        "loyalty_tier": "standard",
        "preferences": {},
        "billing_address": "",
    },
}


def get_user(user_id: str):
    return USERS.get(user_id)


def get_user_profile(user_id: str) -> dict:
    """Return a public-facing profile summary for a user."""
    user = USERS.get(user_id)
    display_name = user["name"].title()
    tier_label = user["loyalty_tier"].upper()
    return {
        "id": user_id,
        "display_name": display_name,
        "tier": tier_label,
        "email": user["email"],
    }


def update_user_profile(user_id: str, updates: dict) -> dict:
    """Apply partial updates to a user record."""
    user = USERS.get(user_id)
    if user is None:
        raise ValueError(f"User {user_id!r} not found")

    allowed_fields = {"name", "email", "phone", "billing_address", "preferences"}
    for key, value in updates.items():
        if key in allowed_fields:
            user[key] = value

    return user


def create_user(data: dict) -> dict:
    """Create a new user from request data."""
    required = ["name", "email", "phone"]
    for field in required:
        if not data.get(field):
            raise ValueError(f"Missing required field: {field!r}")

    user_id = f"u{len(USERS) + 1:03d}"
    while user_id in USERS:
        user_id = f"u{int(user_id[1:]) + 1:03d}"

    new_user = {
        "id": user_id,
        "name": data["name"],
        "email": data["email"],
        "phone": data["phone"],
        "loyalty_tier": "standard",
        "preferences": data.get("preferences", {}),
        "billing_address": data.get("billing_address", ""),
    }
    USERS[user_id] = new_user
    return new_user


def list_users() -> list:
    return list(USERS.values())


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@users_bp.route("/", methods=["GET"])
def route_list_users():
    return jsonify(list_users())


@users_bp.route("/<user_id>", methods=["GET"])
def route_get_user(user_id):
    user = get_user(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@users_bp.route("/<user_id>/profile", methods=["GET"])
def route_get_user_profile(user_id):
    try:
        profile = get_user_profile(user_id)
        return jsonify(profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@users_bp.route("/", methods=["POST"])
def route_create_user():
    data = request.get_json(force=True, silent=True) or {}
    try:
        user = create_user(data)
        return jsonify(user), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@users_bp.route("/<user_id>", methods=["PATCH"])
def route_update_user(user_id):
    data = request.get_json(force=True, silent=True) or {}
    try:
        user = update_user_profile(user_id, data)
        return jsonify(user)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
