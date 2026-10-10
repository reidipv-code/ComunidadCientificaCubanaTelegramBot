
from telegram import Update
from telegram.ext import ContextTypes


TEXTO_AYUDA = (
    "🧪 AYUDA — TRIVIA DE QUÍMICA\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "📌 COMANDOS\n"
    "/start — Iniciar el bot.\n"
    "/help — Mostrar esta ayuda.\n"
    "/trivia 9 — Jugar con preguntas de 9.º.\n"
    "/trivia 8 y 9 — Combinar varios grados.\n"
    "/trivia 8 y 9 y 10 y 11 y 12 — Todos los grados.\n"
    "/perfil — Consultar EXP, nivel y estadísticas.\n"
    "/users — Listado de usuarios (solo administradores).\n\n"
    "🎮 CÓMO SE JUEGA\n"
    "• Cada partida tiene 10 preguntas.\n"
    "• Tienes 25 segundos para responder cada pregunta.\n"
    "• Empiezas con 3 vidas.\n"
    "• Cada respuesta incorrecta o tiempo agotado resta una vida.\n"
    "• Si pierdes las 3 vidas, no recibes EXP.\n\n"
    "⭐ RECOMPENSAS\n"
    "• Terminar con 3 vidas: +100 EXP.\n"
    "• Terminar con 2 vidas: +50 EXP.\n"
    "• Terminar con 1 vida: +25 EXP.\n"
    "• Cada nivel requiere 500 EXP.\n"
    "• El nivel máximo es 500.\n\n"
    "ℹ️ Tu perfil es exclusivo de este bot."
)


async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message

    if mensaje:
        await mensaje.reply_text(TEXTO_AYUDA)
