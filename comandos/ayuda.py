# comandos/ayuda.py

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
    "🧪 CONSTRUCTOR DE SUSTANCIAS\n"
    "/constructor H2O — Descubrir agua por su fórmula.\n"
    "/constructor H2SO4 — Descubrir ácido sulfúrico.\n"
    "/constructor agua — Consultar agua si ya la descubriste.\n"
    "/constructor lista de sustancias — Ver tus descubrimientos.\n"
    "/constructor desafio — Iniciar un desafío de química.\n\n"
    "🎮 DESAFÍO DE QUÍMICA\n"
    "• Debes responder preguntas sobre fórmulas y sustancias.\n"
    "• Las fórmulas pueden escribirse con números normales "
    "o subíndices.\n"
    "• Los nombres no distinguen mayúsculas y minúsculas "
    "ni tildes.\n"
    "• Las fórmulas distinguen mayúsculas y minúsculas.\n"
    "• El tiempo depende de la longitud de la fórmula: "
    "10, 20 o 30 segundos.\n"
    "• Cada respuesta correcta concede 100 EXP.\n"
    "• Una respuesta incorrecta o el tiempo agotado "
    "terminan el desafío sin EXP.\n"
    "• Después de terminar, debes esperar 60 segundos "
    "para iniciar otro desafío.\n\n"
    "📚 DESCUBRIMIENTOS\n"
    "• Primero debes descubrir cada sustancia con su fórmula.\n"
    "• Los descubrimientos se guardan por usuario.\n"
    "• Si repites una fórmula, no se repite el aviso "
    "de descubrimiento.\n\n"
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
    "ℹ️ Tu perfil y tus descubrimientos se guardan por separado "
    "para cada usuario."
)


async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message

    if mensaje:
        await mensaje.reply_text(TEXTO_AYUDA)