from types import SimpleNamespace

from main import describe_media, format_sender_media_message


def test_describe_photo_and_escaped_caption() -> None:
    message = SimpleNamespace(photo=[object()], voice=None, caption="<hi> & bye")

    result = describe_media(message)

    assert result == "📷 Фото\n💬 Подпись: &lt;hi&gt; &amp; bye"


def test_describe_voice_without_caption() -> None:
    message = SimpleNamespace(photo=[], voice=object(), caption=None)

    assert describe_media(message) == "🎤 Голосовое сообщение"


def test_sender_media_message_discloses_username_and_media() -> None:
    message = SimpleNamespace(from_user=SimpleNamespace(username="sender_name"))

    result = format_sender_media_message(message, "🎤 Голосовое сообщение")

    assert "@sender_name" in result
    assert "🎤 Голосовое сообщение" in result
