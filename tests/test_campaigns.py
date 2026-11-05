from datetime import UTC, datetime

import pytest

from app.campaigns import classify_reply, next_business_time


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Please unsubscribe me", "unsubscribe"),
        ("Delivery Status Notification: address not found", "hard_bounce"),
        ("Automatic reply: I am away until Monday", "out_of_office"),
        ("I am not the right person", "wrong_person"),
        ("No thanks, this is not a fit", "objection"),
        ("Circle back next quarter", "not_now"),
        ("Yes, let's book a meeting", "interested"),
        ("Please speak with our operations lead", "referral"),
        ("Thanks for the note", "unknown"),
    ],
)
def test_reply_classification(body: str, expected: str) -> None:
    assert classify_reply("Re: hello", body) == expected


def test_next_business_time_moves_weekend_to_monday() -> None:
    saturday = datetime(2026, 8, 29, 12, tzinfo=UTC)
    result = next_business_time(saturday, "UTC", {"start": 9, "end": 17, "weekdays": [0, 1, 2, 3, 4]})
    assert result == datetime(2026, 8, 31, 9, tzinfo=UTC)


def test_next_business_time_respects_local_timezone() -> None:
    before_open_in_india = datetime(2026, 8, 28, 1, tzinfo=UTC)
    result = next_business_time(before_open_in_india, "Asia/Kolkata", {"start": 9, "end": 17, "weekdays": [0, 1, 2, 3, 4]})
    assert result == datetime(2026, 8, 28, 3, 30, tzinfo=UTC)
