
from telegram import Update
from telegram.ext import ContextTypes

from core.profile_db import (
    nivel_desde_xp,
    obtener_perfil,
    registrar_usuario,
    xp_para_siguiente_nivel,
)


SEGMENTOS_BARRA = 20
XP_POR_NIVEL = 500


def _nombre(user):
    return user.full_name or user.username or f"Jugador {user.id}"


def _barra_xp(xp, nivel):
    if nivel >= 500:
        progreso = XP_POR_NIVEL
    else:
        progreso = int(xp) % XP_POR_NIVEL

    llenos = min(
        SEGMENTOS_BARRA,
        (progreso + 24) // 25,
    )

    barra = (
        "🟩" * llenos
        + "⬜" * (SEGMENTOS_BARRA - llenos)
    )

    return barra, progreso


async def perfil(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    mensaje = update.effective_message

    if not user or not mensaje:
        return

    registrar_usuario(
        user.id,
        _nombre(user),
        user.username,
    )

    datos = obtener_perfil(user.id)

    if not datos:
        await mensaje.reply_text(
            "No pude cargar tu perfil. Inténtalo de nuevo."
        )
        return

    xp = max(0, int(datos.get("xp", 0)))
    nivel = nivel_desde_xp(xp)
    siguiente = xp_para_siguiente_nivel(xp)
    barra, progreso = _barra_xp(xp, nivel)

    texto = (
        "🧪 PERFIL DE QUÍMICA\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 {datos['nombre']}\n"
        f"🆔 ID: {user.id}\n"
        f"🏅 Nivel: {nivel}/500\n"
        f"⭐ EXP total: {xp}\n"
        f"📊 Progreso del nivel: {progreso}/{XP_POR_NIVEL} EXP\n"
        f"{barra}\n"
    )

    if siguiente:
        texto += (
            f"🎯 Te faltan {siguiente} EXP "
            "para el próximo nivel.\n"
        )
    else:
        texto += "🏆 ¡Has alcanzado el nivel máximo!\n"

    texto += (
        f"\n🎮 Partidas: {datos['partidas']}\n"
        f"🏆 Victorias: {datos['victorias']}\n"
        f"🧠 Preguntas correctas: "
        f"{datos['preguntas_correctas']}\n"
        f"📚 Preguntas respondidas: "
        f"{datos['preguntas_respondidas']}\n\n"
        "ℹ️ La EXP se concede al completar las 10 preguntas. "
        "Si pierdes las 3 vidas, no recibes EXP.\n"
        "ℹ️ Este perfil y su EXP son exclusivos de Trivia de Química."
    )

    await mensaje.reply_text(texto)
