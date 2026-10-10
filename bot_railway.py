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

from comandos.perfil import perfil
from comandos.trivia import trivia
from core.profile_db import inicializar_db, registrar_usuario
from juegos.trivia import responder_boton

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)

logger = logging.getLogger(__name__)
TOKEN = os.getenv("BOT_TOKEN", "").strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user:
        registrar_usuario(
            user.id,
            user.full_name or user.username or f"Jugador {user.id}",
            user.username,
        )

    await update.effective_message.reply_text(
        "🧪 ¡Bienvenido a la Trivia de Química!\n\n"
        "Responde 10 preguntas con 3 vidas y 10 segundos por pregunta.\n\n"
        "🎮 Comandos disponibles:\n"
        "• /trivia 9\n"
        "• /trivia 8 y 9\n"
        "• /trivia 8 y 9 y 10 y 11 y 12\n"
        "• /perfil\n\n"
        "⭐ Gana EXP respondiendo correctamente.\n"
        "👤 Tu perfil se crea automáticamente.\n"
        "🔒 Tu nivel y EXP son independientes de otros bots."
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    if context.error:
        logger.error(
            "Error procesando una actualización",
            exc_info=(
                type(context.error),
                context.error,
                context.error.__traceback__,
            ),
        )


def main():
    if not TOKEN:
        raise RuntimeError(
            "Falta BOT_TOKEN en las variables de entorno de Railway."
        )

    inicializar_db()

    application = Application.builder().token(TOKEN).build()

    if application.job_queue is None:
        raise RuntimeError(
            "JobQueue no disponible. Instala "
            "python-telegram-bot[job-queue]."
        )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("trivia", trivia))
    application.add_handler(CommandHandler("perfil", perfil))

    application.add_handler(
        CallbackQueryHandler(
            responder_boton,
            pattern=r"^qt\|",
        )
    )

    application.add_error_handler(error_handler)

    logger.info("Trivia de Química iniciando...")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
