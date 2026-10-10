python
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from comandos.ayuda import ayuda
from comandos.perfil import perfil
from comandos.trivia import trivia
from comandos.usuarios import users
from core.profile_db import inicializar_db, registrar_usuario
from juegos.trivia import responder_boton

load_dotenv()

# Zona horaria exclusiva de Cuba.
ZONA_HORARIA = ZoneInfo("America/Havana")


def hora_cuba() -> datetime:
    """Devuelve la fecha y hora actual de Cuba."""
    return datetime.now(ZONA_HORARIA)


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)

logger = logging.getLogger(__name__)
TOKEN = os.getenv("BOT_TOKEN", "").strip()


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    mensaje = update.effective_message

    if user and mensaje:
        registrar_usuario(
            user.id,
            user.full_name or user.username or f"Jugador {user.id}",
            user.username,
        )

        await mensaje.reply_text(
            "🧪 ¡Bienvenido a la Trivia de Química!\n\n"
            "Responde 10 preguntas, con 3 vidas y 25 segundos por pregunta.\n\n"
            "📌 COMANDOS\n"
            "• /trivia 9 — Jugar con preguntas de 9.º grado.\n"
            "• /trivia 8 y 9 — Combinar grados.\n"
            "• /perfil — Consultar tu EXP y estadísticas.\n"
            "• /help — Ver todos los comandos y reglas.\n\n"
            "Tu perfil y tu EXP son exclusivos de este bot."
        )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    if context.error:
        logger.error(
            "Error procesando update",
            exc_info=(
                type(context.error),
                context.error,
                context.error.__traceback__,
            ),
        )


def main():
    if not TOKEN:
        raise RuntimeError(
            "Falta BOT_TOKEN en las variables de entorno."
        )

    logger.info(
        "Hora de Cuba al iniciar: %s",
        hora_cuba().strftime("%Y-%m-%d %H:%M:%S %Z"),
    )

    inicializar_db()

    application = Application.builder().token(TOKEN).build()

    if application.job_queue is None:
        raise RuntimeError(
            "JobQueue no disponible. Instala "
            "python-telegram-bot[job-queue]."
        )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CommandHandler(["help", "ayuda"], ayuda)
    )
    application.add_handler(CommandHandler("trivia", trivia))
    application.add_handler(CommandHandler("perfil", perfil))
    application.add_handler(CommandHandler("users", users))

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
```
