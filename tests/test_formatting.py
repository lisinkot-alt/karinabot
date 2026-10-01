from html import escape
from types import SimpleNamespace

from main import format_anonymous_message, format_sender_message


def test_anonymous_message_escapes_text_and_has_no_sender_identity() -> None:
    text = '<hi> & "there"\nsecond line'
    result = format_anonymous_message(text)

    assert escape(text) in result
    assert "@secret_user" not in result
    assert "анонимное сообщение" in result


def test_sender_message_includes_username_and_escaped_original_text() -> None:
    text = "<hello> & welcome"
    message = SimpleNamespace(from_user=SimpleNamespace(username="sender_name"))

    result = format_sender_message(message, text)

    assert "@sender_name" in result
    assert escape(text) in result


def test_sender_message_notes_missing_username() -> None:
    message = SimpleNamespace(from_user=SimpleNamespace(username=None))

    result = format_sender_message(message, "message")

    assert "Username не установлен" in result
