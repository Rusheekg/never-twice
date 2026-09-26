"""
Failing tests that PROVE each confirmed bug.

Run with:  pytest tests/ -v
All tests should FAIL before the bugs are fixed.
All tests should PASS after the bugs are fixed.

No real external services are used — requests are mocked with unittest.mock.
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Make the app package importable without installing it
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


# ===========================================================================
# BUG 1 — app/users.py :: get_user_profile
# Pattern: missing-none-check
# USERS.get(user_id) returns None for an unknown user_id, then
# user["name"] is subscripted without a guard → TypeError.
# After the fix a ValueError (or suitable exception) should be raised instead.
# ===========================================================================

def test_get_user_profile_missing_none_check():
    """get_user_profile with an unknown user_id must raise ValueError, not crash."""
    from users import get_user_profile
    # Expect a ValueError (the fix) — currently raises TypeError (the bug)
    with pytest.raises(ValueError, match="not found"):
        get_user_profile("nonexistent_user")


# ===========================================================================
# BUG 2 — app/bookings.py :: get_booking_summary
# Pattern: missing-none-check
# BOOKINGS.get(booking_id) returns None for an unknown booking_id, then
# booking["user_id"] is subscripted → TypeError.
# After the fix a ValueError should be raised.
# ===========================================================================

def test_get_booking_summary_missing_none_check():
    """get_booking_summary with an unknown booking_id must raise ValueError, not crash."""
    from bookings import get_booking_summary
    with pytest.raises(ValueError, match="not found"):
        get_booking_summary("nonexistent_booking")


# ===========================================================================
# BUG 3 — app/rooms.py :: get_room_details  (unknown room_id → room is None)
# Pattern: missing-none-check
# ROOMS.get(room_id) returns None → room["description"] → TypeError.
# After the fix a ValueError should be raised.
# ===========================================================================

def test_get_room_details_unknown_room_missing_none_check():
    """get_room_details with an unknown room_id must raise ValueError, not crash."""
    from rooms import get_room_details
    with pytest.raises(ValueError, match="not found"):
        get_room_details("nonexistent_room")


# ===========================================================================
# BUG 3b — app/rooms.py :: get_room_details  (description field is None)
# Pattern: missing-none-check
# Room r110 has description=None; room["description"].strip() → AttributeError.
# After the fix the function must handle a None description gracefully.
# ===========================================================================

def test_get_room_details_none_description():
    """get_room_details for a room with description=None must not crash."""
    from rooms import get_room_details
    # r110 has description=None in the ROOMS store; calling .strip() on None raises AttributeError
    # After the fix, the function should return the details without crashing
    result = get_room_details("r110")
    # The description should be an empty string or None, but not an AttributeError
    assert result["description"] is not None  # fix should normalise to ""


# ===========================================================================
# BUG 4 — app/notifications.py :: send_sms_notification
# Pattern: http-no-timeout
# http.post() has no timeout= → hangs indefinitely when gateway is slow.
# After the fix a RuntimeError("timed out") is raised in ≤ 5 seconds.
# ===========================================================================

def test_send_sms_notification_timeout():
    """send_sms_notification must raise RuntimeError on gateway timeout, not hang."""
    import requests.exceptions
    from notifications import send_sms_notification

    with patch("notifications.http") as mock_http:
        mock_http.post.side_effect = requests.exceptions.Timeout("gateway timed out")
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException
        with pytest.raises(RuntimeError, match="timed out"):
            send_sms_notification("u001", "Test message")


def test_send_sms_notification_connection_error():
    """send_sms_notification must raise RuntimeError on connection failure, not propagate."""
    import requests.exceptions
    from notifications import send_sms_notification

    with patch("notifications.http") as mock_http:
        mock_http.post.side_effect = requests.exceptions.ConnectionError("refused")
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException
        with pytest.raises(RuntimeError, match="unreachable"):
            send_sms_notification("u001", "Test message")


def test_send_sms_notification_has_timeout_kwarg():
    """send_sms_notification must pass timeout= to http.post()."""
    from notifications import send_sms_notification

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "sent", "ref": "ntf_abc123"}

    with patch("notifications.http") as mock_http:
        mock_http.post.return_value = mock_response
        mock_http.exceptions.Timeout = Exception
        mock_http.exceptions.RequestException = Exception
        send_sms_notification("u001", "Test message")

    call_kwargs = mock_http.post.call_args
    assert "timeout" in call_kwargs.kwargs or (
        len(call_kwargs.args) > 1 and "timeout" in str(call_kwargs)
    ), "http.post() must be called with a timeout= argument"


# ===========================================================================
# BUG 5 — app/payments.py :: process_payment
# Pattern: http-no-timeout
# http.post() has no timeout= → hangs indefinitely when gateway is slow.
# After the fix a RuntimeError is raised on timeout.
# ===========================================================================

def test_process_payment_timeout():
    """process_payment must raise RuntimeError on gateway timeout, not hang."""
    import requests.exceptions
    from payments import process_payment

    with patch("payments.http") as mock_http:
        mock_http.post.side_effect = requests.exceptions.Timeout("gateway timed out")
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException
        with pytest.raises(RuntimeError, match="timed out"):
            process_payment("bk001", "u001", 149.00)


def test_process_payment_connection_error():
    """process_payment must raise RuntimeError on connection failure, not propagate."""
    import requests.exceptions
    from payments import process_payment

    with patch("payments.http") as mock_http:
        mock_http.post.side_effect = requests.exceptions.ConnectionError("refused")
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException
        with pytest.raises(RuntimeError, match="unreachable"):
            process_payment("bk001", "u001", 149.00)


def test_process_payment_has_timeout_kwarg():
    """process_payment must pass timeout= to http.post()."""
    from payments import process_payment

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "transaction_id": "gw_xyz"}

    with patch("payments.http") as mock_http:
        mock_http.post.return_value = mock_response
        mock_http.exceptions.Timeout = Exception
        mock_http.exceptions.RequestException = Exception
        process_payment("bk001", "u001", 149.00)

    call_kwargs = mock_http.post.call_args
    assert "timeout" in call_kwargs.kwargs or (
        len(call_kwargs.args) > 1 and "timeout" in str(call_kwargs)
    ), "http.post() must be called with a timeout= argument"


# ===========================================================================
# BUG 6 — app/bookings.py :: create_booking
# Pattern: naive-aware-datetime
# naive booking_start compared with aware request_deadline → TypeError (or
# silent wrong result).  After the fix the comparison works correctly.
# ===========================================================================

def test_create_booking_naive_aware_datetime():
    """create_booking must not raise TypeError when comparing booking_start vs now."""
    from bookings import create_booking, BOOKINGS

    # We patch enough dependencies to exercise the datetime comparison path.
    # Use a future date so the check-in validation should PASS (not raise ValueError).
    future_date = "2099-01-01"
    checkout_date = "2099-01-03"

    with patch("bookings.get_user") as mock_user, \
         patch("bookings.get_room") as mock_room, \
         patch("bookings.update_room_status"), \
         patch("rooms.calculate_room_cost", return_value=200.0):

        mock_user.return_value = {"id": "u001", "name": "Alice"}
        mock_room.return_value = {
            "id": "r101", "status": "available", "max_guests": 2,
            "price_per_night": 100.0
        }

        # This should NOT raise TypeError — if it does, the naive/aware bug is present
        try:
            booking = create_booking("u001", "r101", future_date, checkout_date, 1)
        except TypeError as exc:
            pytest.fail(
                f"create_booking raised TypeError due to naive/aware datetime mismatch: {exc}"
            )

        # Clean up the in-memory store entry created by the call
        booking_id = booking["id"]
        if booking_id in BOOKINGS:
            del BOOKINGS[booking_id]


def test_create_booking_past_date_rejected():
    """create_booking must correctly reject a check-in date in the past."""
    from bookings import create_booking

    past_date = "2000-01-01"
    checkout_date = "2000-01-03"

    with patch("bookings.get_user") as mock_user, \
         patch("bookings.get_room") as mock_room, \
         patch("bookings.update_room_status"), \
         patch("rooms.calculate_room_cost", return_value=200.0):

        mock_user.return_value = {"id": "u001", "name": "Alice"}
        mock_room.return_value = {
            "id": "r101", "status": "available", "max_guests": 2,
            "price_per_night": 100.0
        }

        # Must raise ValueError("Check-in date cannot be in the past"),
        # NOT TypeError from naive/aware comparison
        try:
            with pytest.raises(ValueError, match="past"):
                create_booking("u001", "r101", past_date, checkout_date, 1)
        except TypeError as exc:
            pytest.fail(
                f"create_booking raised TypeError instead of ValueError — "
                f"naive/aware datetime bug is present: {exc}"
            )


# ===========================================================================
# BUG 7 — app/bookings.py :: get_booking_duration
# Pattern: naive-aware-datetime
# naive check_in_dt subtracted from aware now → TypeError.
# After the fix the subtraction works correctly and returns int days.
# ===========================================================================

def test_get_booking_duration_naive_aware_datetime():
    """get_booking_duration must not raise TypeError due to naive/aware mismatch."""
    from bookings import get_booking_duration

    try:
        days = get_booking_duration("bk001")
    except TypeError as exc:
        pytest.fail(
            f"get_booking_duration raised TypeError due to naive/aware datetime mismatch: {exc}"
        )

    assert isinstance(days, int), f"Expected int, got {type(days)}"
