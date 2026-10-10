import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from comandos.trivia import trivia
from juegos.trivia import responder_boton


load_dotenv()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "").strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🧪 ¡Bienvenido a la Trivia de Química!\n\n"
        "Responde 10 preguntas, con 3 vidas y 10 segundos por pregunta.\n\n"
        "Comandos:\n"
        "• /trivia 8\n"
        "• /trivia 9\n"
        "• /trivia 8 y 9\n"
        "• /trivia 8 y 10 y 12\n"
        "• /trivia 8 y 9 y 10 y 11 y 12\n\n"
        "La EXP se comparte con ReidiStudiosBot. Debes estar registrado allí."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(
        "Error procesando update",
        exc_info=(type(context.error), context.error, context.error.__traceback__)
        if context.error else None,
    )


def main():
    if not TOKEN:
        raise RuntimeError("Falta BOT_TOKEN en las variables de entorno.")

    application = Application.builder().token(TOKEN).build()

    if application.job_queue is None:
        raise RuntimeError(
            "JobQueue no disponible. Instala python-telegram-bot[job-queue]."
        )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("trivia", trivia))
    application.add_handler(
        CallbackQueryHandler(responder_boton, pattern=r"^qt\|")
    )
    application.add_error_handler(error_handler)

    logger.info("Trivia de Química iniciando...")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
