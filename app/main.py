from flask import Flask
from users import users_bp
from rooms import rooms_bp
from bookings import bookings_bp
from payments import payments_bp
from notifications import notifications_bp

app = Flask(__name__)

app.register_blueprint(users_bp, url_prefix="/users")
app.register_blueprint(rooms_bp, url_prefix="/rooms")
app.register_blueprint(bookings_bp, url_prefix="/bookings")
app.register_blueprint(payments_bp, url_prefix="/payments")
app.register_blueprint(notifications_bp, url_prefix="/notifications")


@app.route("/health")
def health():
    return {"status": "ok", "service": "hotel-booking-api"}


@app.errorhandler(404)
def not_found(e):
    return {"error": "Resource not found"}, 404


@app.errorhandler(405)
def method_not_allowed(e):
    return {"error": "Method not allowed"}, 405


@app.errorhandler(500)
def internal_error(e):
    return {"error": "Internal server error"}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
