# Hotel Booking API

A small Flask REST API simulating a hotel booking system. Bookings, users, rooms,
payments, and notifications are all stored in-memory — no database required.

---

## Project layout

```
never-twice/
├── app/
│   ├── main.py            # Flask application factory & blueprint registration
│   ├── users.py           # User management (CRUD + profile)
│   ├── rooms.py           # Room catalogue, availability, status updates
│   ├── bookings.py        # Booking lifecycle (create / confirm / cancel)
│   ├── payments.py        # Payment processing and refunds
│   ├── notifications.py   # Email and SMS notification dispatch
│   ├── mock_services.py   # Standalone mock payment & notification gateway
│   └── requirements.txt   # Python dependencies
└── README.md
```

---

## Prerequisites

- Python 3.11+
- pip

---

## Installation

```bash
cd app
pip install -r requirements.txt
```

---

## Running the application

### 1. Start the mock external services (port 5001)

Open a **separate terminal**:

```bash
cd app
python mock_services.py
```

Verify it is up:

```bash
curl http://localhost:5001/health
```

### 2. Start the main API (port 5000)

```bash
cd app
python main.py
```

Verify it is up:

```bash
curl http://localhost:5000/health
```

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | /users/ | List all users |
| POST | /users/ | Create a user |
| GET | /users/{id} | Get a user |
| PATCH | /users/{id} | Update a user |
| GET | /users/{id}/profile | Get public profile |
| GET | /rooms/ | Search/list rooms |
| GET | /rooms/available | List available rooms |
| GET | /rooms/{id} | Get room record |
| GET | /rooms/{id}/details | Get formatted room details |
| PATCH | /rooms/{id}/status | Update room status |
| GET | /bookings/ | List bookings (optional ?user_id=) |
| POST | /bookings/ | Create a booking |
| GET | /bookings/{id} | Get a booking |
| GET | /bookings/{id}/summary | Human-readable booking summary |
| POST | /bookings/{id}/cancel | Cancel a booking |
| GET | /bookings/{id}/duration | Elapsed nights since check-in |
| GET | /payments/ | List payments (optional ?user_id=) |
| POST | /payments/charge | Process a payment |
| GET | /payments/{id} | Get a payment |
| POST | /payments/{id}/refund | Refund a payment |
| GET | /payments/status/{booking_id} | Payment status by booking |
| POST | /notifications/email | Send an email notification |
| POST | /notifications/sms | Send an SMS notification |
| GET | /notifications/ | List notification log |

---

## Simulating failures and slow responses (mock services)

All mock endpoints accept query parameters to inject faults — useful for testing
error handling, timeouts, and retry logic in the main API.

| Parameter | Effect |
|-----------|--------|
| `?fail=1` | Always return a failure response |
| `?slow=N` | Sleep N seconds before responding (e.g. `?slow=10`) |
| `?random_fail=1` | ~10 % chance of failure per request |

**Example — force a payment failure:**

```bash
# Hit the mock gateway directly
curl -X POST "http://localhost:5001/payment/charge?fail=1" \
     -H "Content-Type: application/json" \
     -d '{"booking_id":"bk001","user_id":"u001","amount":100}'

# Then call the main API's /payments/charge — it will hit the same mock
# and propagate the error
curl -X POST http://localhost:5000/payments/charge \
     -H "Content-Type: application/json" \
     -d '{"booking_id":"bk001","user_id":"u001","amount":100}'
```

**Example — trigger a timeout:**

```bash
curl "http://localhost:5001/notify?slow=30"
```

---

## Sample requests

### Create a booking

```bash
curl -X POST http://localhost:5000/bookings/ \
     -H "Content-Type: application/json" \
     -d '{
           "user_id": "u001",
           "room_id": "r305",
           "check_in": "2025-09-01",
           "check_out": "2025-09-04",
           "guests": 2,
           "special_requests": "Extra pillows please"
         }'
```

### Get a booking summary

```bash
curl http://localhost:5000/bookings/bk001/summary
```

### Process a payment

```bash
curl -X POST http://localhost:5000/payments/charge \
     -H "Content-Type: application/json" \
     -d '{"booking_id":"bk_NEW_ID","user_id":"u001","amount":299}'
```

---

## Running tests

```bash
cd app
pytest -v
```

> Tests are located in `tests/` (not included in this scaffold — add your own).
