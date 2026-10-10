import re

from telegram import Update
from telegram.ext import ContextTypes

from juegos.trivia import iniciar_partida


def _extraer_grados(argumentos):
    texto = " ".join(argumentos or [])
    encontrados = re.findall(r"(?<!\d)(8|9|10|11|12)(?!\d)", texto)
    return sorted({int(g) for g in encontrados})


async def trivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grados = _extraer_grados(context.args)

    if not grados:
        await update.effective_message.reply_text(
            "🧪 TRIVIA DE QUÍMICA\n\n"
            "Elige uno o varios grados del 8.º al 12.º.\n\n"
            "Ejemplos:\n"
            "/trivia 9\n"
            "/trivia 8 y 9\n"
            "/trivia 8 y 10 y 12\n"
            "/trivia 8 y 9 y 10 y 11 y 12"
        )
        return

    await iniciar_partida(update, context, grados)
