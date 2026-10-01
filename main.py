"""Telegram bot that forwards messages to Karina in two formats."""

from __future__ import annotations

import asyncio
import logging
import os
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
KARINA_CHAT_ID_RAW = os.getenv("KARINA_CHAT_ID", "").strip()
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram/webhook").strip()


def get_configuration() -> tuple[str, int]:
    """Read and validate required environment configuration."""
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_TOKEN_FROM_BOTFATHER_HERE":
        raise RuntimeError("BOT_TOKEN is missing. Set it in the environment or .env file.")
    if not KARINA_CHAT_ID_RAW or KARINA_CHAT_ID_RAW == "PASTE_KARINA_NUMERIC_CHAT_ID_HERE":
        raise RuntimeError("KARINA_CHAT_ID is missing. Set it in the environment or .env file.")
    try:
        chat_id = int(KARINA_CHAT_ID_RAW)
    except ValueError as exc:
        raise RuntimeError("KARINA_CHAT_ID must be a numeric Telegram chat ID.") from exc
    return BOT_TOKEN, chat_id


def format_anonymous_message(text: str) -> str:
    """Build the public-facing message without sender details."""
    return (
        "💌 <b>Карина, вам пришло новое анонимное сообщение!</b> ✨\n\n"
        f"💬 {escape(text)}\n\n"
        "🌷 <i>Передано через анонимного бота</i>"
    )


def format_sender_message(message: Message, text: str) -> str:
    """Build the private sender-identification message for Karina."""
    user = message.from_user
    if user is None:
        sender = "Username не установлен"
    elif user.username:
        sender = f"@{escape(user.username)}"
    else:
        sender = "Username не установлен"
    return (
        "🔎 <b>Данные отправителя</b>\n\n"
        f"👤 <b>Пользователь:</b> {sender}\n"
        f"📝 <b>Содержание:</b>\n{escape(text)}"
    )


def describe_media(message: Message) -> str | None:
    """Return the media type and optional caption for sender notification."""
    if message.photo:
        media = "📷 Фото"
    elif message.voice:
        media = "🎤 Голосовое сообщение"
    else:
        return None

    caption = (message.caption or "").strip()
    if caption:
        media += f"\n💬 Подпись: {escape(caption)}"
    return media


def format_sender_media_message(message: Message, media_description: str) -> str:
    """Build the sender-identification message for a photo or voice note."""
    user = message.from_user
    if user is not None and user.username:
        sender = f"@{escape(user.username)}"
    else:
        sender = "Username не установлен"
    return (
        "🔎 <b>Данные отправителя</b>\n\n"
        f"👤 <b>Пользователь:</b> {sender}\n"
        f"📎 <b>Отправлено:</b>\n{media_description}"
    )


async def main() -> None:
    token, karina_chat_id = get_configuration()
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer(
            "👋 <b>Привет!</b> Здесь можно отправить Карине анонимное сообщение.\n\n"
        )

    @dispatcher.message(Command("cancel"))
    async def cancel(message: Message) -> None:
        await message.answer("Отправка не выполняется. Если захотите написать Карине, просто отправьте текст.")

    @dispatcher.message(F.text)
    async def forward_text(message: Message) -> None:
        text = (message.text or "").strip()
        if not text:
            await message.answer("Пожалуйста, отправьте непустой текст.")
            return
        try:
            await bot.send_message(karina_chat_id, format_anonymous_message(text))
            await bot.send_message(karina_chat_id, format_sender_message(message, text))
        except Exception:
            logger.exception("Could not deliver a message to the configured recipient")
            await message.answer(
                "Не удалось доставить сообщение Карине. Попробуйте позже или свяжитесь с администратором бота."
            )
            return
        await message.answer("✅ Сообщение отправлено Карине!")

    @dispatcher.message(F.photo | F.voice)
    async def forward_media(message: Message) -> None:
        media_description = describe_media(message)
        if media_description is None:
            return

        try:
            if message.photo:
                await bot.send_message(
                    karina_chat_id,
                    "💌 <b>Карина, вам пришло новое анонимное сообщение!</b> ✨\n\n"
                    "📷 <i>Отправитель прислал фото</i> 🌷",
                )
                await bot.send_photo(
                    karina_chat_id,
                    message.photo[-1].file_id,
                    caption="📷 <b>Анонимное фото</b>",
                )
            else:
                await bot.send_message(
                    karina_chat_id,
                    "💌 <b>Карина, вам пришло новое анонимное сообщение!</b> ✨\n\n"
                    "🎤 <i>Отправитель прислал голосовое сообщение</i> 🌷",
                )
                await bot.send_voice(
                    karina_chat_id,
                    message.voice.file_id,
                    caption="🎤 <b>Анонимное голосовое сообщение</b>",
                )

            await bot.send_message(
                karina_chat_id,
                format_sender_media_message(message, media_description),
            )
            if message.photo:
                await bot.send_photo(
                    karina_chat_id,
                    message.photo[-1].file_id,
                    caption="🔎 <b>Фото от отправителя</b>",
                )
            else:
                await bot.send_voice(
                    karina_chat_id,
                    message.voice.file_id,
                    caption="🔎 <b>Голосовое сообщение от отправителя</b>",
                )
        except Exception:
            logger.exception("Could not deliver media to the configured recipient")
            await message.answer(
                "Не удалось доставить сообщение Карине. Попробуйте позже или свяжитесь с администратором бота."
            )
            return
        await message.answer("✅ Фото или голосовое сообщение отправлено Карине!")

    @dispatcher.message()
    async def unsupported_message(message: Message) -> None:
        await message.answer("Бот принимает текст, фото и голосовые сообщения. Попробуйте отправить один из этих типов.")

    webhook_url = (
        os.getenv("WEBHOOK_URL", "").strip()
        or os.getenv("RENDER_EXTERNAL_URL", "").strip()
    ).rstrip("/")
    if webhook_url:
        app = web.Application()
        app.router.add_get("/", lambda request: web.Response(text="Telegram bot is running."))
        app.router.add_get("/health", lambda request: web.Response(text="ok"))
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dispatcher,
            bot=bot,
            secret_token=os.getenv("WEBHOOK_SECRET", "").strip() or None,
        )
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dispatcher, bot=bot)

        async def on_startup(application: web.Application) -> None:
            await bot.set_webhook(
                f"{webhook_url}{WEBHOOK_PATH}",
                secret_token=os.getenv("WEBHOOK_SECRET", "").strip() or None,
                allowed_updates=dispatcher.resolve_used_update_types(),
            )

        async def on_shutdown(application: web.Application) -> None:
            await bot.delete_webhook()
            await bot.session.close()

        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
        await site.start()
        logger.info("Webhook server listening on port %s", os.getenv("PORT", "10000"))
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
    else:
        try:
            await dispatcher.start_polling(bot)
        finally:
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
