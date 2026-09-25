"""
Failing tests for each confirmed bug found in the Never Twice audit.

Each test is named after the function and pattern it targets.
All tests are expected to FAIL before the bugs are fixed.
External HTTP calls are mocked so the tests never need the mock services running.
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
# BUG 1 — app/users.py :: get_user_profile — missing None-guard (PM-001)
# ===========================================================================
def test_get_user_profile_missing_none_check():
    """
    get_user_profile() does USERS.get(user_id) and immediately subscripts the
    result without checking for None.  Calling it with an unknown user_id must
    raise ValueError (the correct behaviour) but instead raises TypeError.
    This test asserts the correct ValueError, which currently fails because a
    TypeError is raised instead.
    """
    import users
    with pytest.raises(ValueError):
        users.get_user_profile("nonexistent-user-id")


# ===========================================================================
# BUG 2 — app/bookings.py :: get_booking_summary — missing None-guard (PM-001)
# ===========================================================================
def test_get_booking_summary_missing_none_check():
    """
    get_booking_summary() does BOOKINGS.get(booking_id) and immediately
    subscripts the result without checking for None.  Calling it with an
    unknown booking_id must raise ValueError but instead raises TypeError.
    """
    import bookings
    with pytest.raises(ValueError):
        bookings.get_booking_summary("nonexistent-booking-id")


# ===========================================================================
# BUG 3 — app/rooms.py :: get_room_details — missing None-guard +
#          None description field (PM-001)
# ===========================================================================
def test_get_room_details_missing_none_check_unknown_room():
    """
    get_room_details() does ROOMS.get(room_id) without a None guard.
    An unknown room_id should raise ValueError but instead raises TypeError
    because the code tries to call .strip() on None (the unguarded room).
    """
    import rooms
    with pytest.raises(ValueError):
        rooms.get_room_details("nonexistent-room-id")


def test_get_room_details_none_description_field():
    """
    Room r110 has description=None in the data store.
    get_room_details("r110") tries room["description"].strip() which raises
    AttributeError because None has no .strip() method.
    The correct behaviour would be to handle None description gracefully.
    """
    import rooms
    # r110 exists but has description=None; .strip() on None must not crash
    result = rooms.get_room_details("r110")
    # If we reach here the function handled None gracefully
    assert result["description"] is not None or result["description"] == ""


# ===========================================================================
# BUG 4 — app/notifications.py :: send_sms_notification —
#          no timeout / no error handling (PM-002)
# ===========================================================================
def test_send_sms_notification_timeout_raises_runtime_error():
    """
    send_sms_notification() calls requests.post() with no timeout and no
    try/except.  When the gateway times out, requests raises
    requests.exceptions.Timeout which propagates as-is instead of being
    caught and re-raised as RuntimeError.
    This test expects RuntimeError (the correct behaviour) but currently gets
    requests.exceptions.Timeout (the bug).
    """
    import requests
    import notifications

    timeout_exc = requests.exceptions.Timeout("gateway timed out")

    with patch("notifications.http") as mock_http:
        mock_http.post.side_effect = timeout_exc
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException

        with pytest.raises(RuntimeError, match="timed out"):
            notifications.send_sms_notification("u001", "Your booking is confirmed.")


def test_send_sms_notification_connection_error_raises_runtime_error():
    """
    send_sms_notification() has no try/except, so a connection error propagates
    as requests.exceptions.ConnectionError instead of RuntimeError.
    """
    import requests
    import notifications

    conn_exc = requests.exceptions.ConnectionError("gateway unreachable")

    with patch("notifications.http") as mock_http:
        mock_http.post.side_effect = conn_exc
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException

        with pytest.raises(RuntimeError, match="unreachable"):
            notifications.send_sms_notification("u001", "Your booking is confirmed.")


# ===========================================================================
# BUG 5 — app/payments.py :: process_payment —
#          no timeout / no error handling (PM-002)
# ===========================================================================
def test_process_payment_timeout_raises_runtime_error():
    """
    process_payment() calls requests.post() with no timeout and no try/except.
    A gateway timeout must raise RuntimeError (correct) but currently propagates
    as raw requests.exceptions.Timeout.
    """
    import requests
    import payments

    timeout_exc = requests.exceptions.Timeout("payment gateway timed out")

    with patch("payments.http") as mock_http:
        mock_http.post.side_effect = timeout_exc
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException

        with pytest.raises(RuntimeError, match="timed out"):
            payments.process_payment("bk001", "u001", 100.0)


def test_process_payment_connection_error_raises_runtime_error():
    """
    process_payment() has no try/except, so a connection failure propagates as
    requests.exceptions.ConnectionError instead of RuntimeError.
    """
    import requests
    import payments

    conn_exc = requests.exceptions.ConnectionError("payment gateway down")

    with patch("payments.http") as mock_http:
        mock_http.post.side_effect = conn_exc
        mock_http.exceptions.Timeout = requests.exceptions.Timeout
        mock_http.exceptions.RequestException = requests.exceptions.RequestException

        with pytest.raises(RuntimeError, match="unreachable"):
            payments.process_payment("bk001", "u001", 100.0)


# ===========================================================================
# BUG 6 — app/bookings.py :: create_booking —
#          naive/aware datetime mismatch (PM-003)
# ===========================================================================
def test_create_booking_naive_aware_datetime_mismatch():
    """
    create_booking() compares a timezone-naive datetime.strptime() result
    against a timezone-aware datetime.now(timezone.utc).  On Python 3.9 this
    raises TypeError: can't compare offset-naive and offset-aware datetimes.
    The test expects ValueError (the correct domain error) but currently gets
    TypeError from the naive/aware mismatch.

    We use a future check-in date so the past-date validation is the ONLY
    thing that can raise, letting the naive/aware comparison run.
    We mock get_user and get_room so no real data is needed.
    """
    import bookings
    from unittest.mock import patch

    future_date = "2099-12-31"
    future_out = "2100-01-05"

    mock_user = {"id": "u001", "name": "Test"}
    mock_room = {
        "id": "r101", "number": "101", "type": "standard",
        "status": "available", "max_guests": 2, "price_per_night": 89.0,
    }

    with patch("bookings.get_user", return_value=mock_user), \
         patch("bookings.get_room", return_value=mock_room), \
         patch("bookings.update_room_status"), \
         patch("rooms.calculate_room_cost", return_value=445.0):
        # Should succeed (future dates, valid room/user) — but the naive/aware
        # comparison on line 71 will raise TypeError first.
        # We expect no TypeError, i.e. the function should complete without error.
        # Currently it DOES raise TypeError, so the test will fail.
        result = bookings.create_booking("u001", "r101", future_date, future_out, 2)
        assert result["check_in"] == future_date


# ===========================================================================
# BUG 7 — app/bookings.py :: get_booking_duration —
#          naive/aware datetime mismatch (PM-003)
# ===========================================================================
def test_get_booking_duration_naive_aware_datetime_mismatch():
    """
    get_booking_duration() subtracts a timezone-aware datetime.now(timezone.utc)
    from a timezone-naive datetime.strptime() result.  This raises:
        TypeError: can't subtract offset-naive and offset-aware datetimes
    The test expects a plain integer return value, which currently fails.
    """
    import bookings

    # bk001 exists in the in-memory store
    result = bookings.get_booking_duration("bk001")
    assert isinstance(result, int)
