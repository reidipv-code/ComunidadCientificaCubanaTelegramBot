from telegram import Update
from telegram.ext import ContextTypes

from core.profile_db import (
    nivel_desde_xp,
    obtener_perfil,
    registrar_usuario,
    xp_para_siguiente_nivel,
)


def _nombre(user):
    return user.full_name or user.username or f"Jugador {user.id}"


async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mensaje = update.effective_message

    if not user or not mensaje:
        return

    # Crear el perfil automáticamente si no existe.
    registrar_usuario(
        user.id,
        _nombre(user),
        user.username,
    )

    datos = obtener_perfil(user.id)

    if not datos:
        await mensaje.reply_text(
            "❌ No pude cargar tu perfil. Inténtalo de nuevo."
        )
        return

    xp = int(datos["xp"])
    nivel = nivel_desde_xp(xp)
    siguiente = xp_para_siguiente_nivel(xp)

    if nivel >= 500:
        porcentaje = 100
    else:
        porcentaje = (xp % 500) / 5

    bloques = min(10, max(0, int(porcentaje // 10)))
    barra = "🟩" * bloques + "⬜" * (10 - bloques)

    texto = (
        "🧪 PERFIL DE QUÍMICA\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 Nombre: {datos['nombre']}\n"
        f"🆔 ID: {user.id}\n"
        f"🏅 Nivel: {nivel}/500\n"
        f"⭐ EXP: {xp}\n"
        f"📊 Progreso: {barra}\n"
    )

    if siguiente:
        texto += (
            f"🎯 EXP para el siguiente nivel: {siguiente}\n"
        )
    else:
        texto += "🏆 ¡Has alcanzado el nivel máximo!\n"

    texto += (
        "\n📈 ESTADÍSTICAS\n"
        f"🎮 Partidas: {datos['partidas']}\n"
        f"🏆 Partidas completadas: {datos['victorias']}\n"
        f"🧠 Respuestas correctas: "
        f"{datos['preguntas_correctas']}\n"
        f"📚 Preguntas respondidas: "
        f"{datos['preguntas_respondidas']}\n\n"
        "🔒 Perfil exclusivo de Trivia de Química."
    )

    await mensaje.reply_text(texto)
