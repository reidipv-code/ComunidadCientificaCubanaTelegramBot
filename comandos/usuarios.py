
import os
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from core.profile_db import listar_usuarios


LIMITE_MENSAJE = 3500


def _admins_configurados():
    raw = os.getenv("ADMIN_IDS", "").strip()

    if not raw:
        raw = os.getenv("ADMIN_ID", "").strip()

    admins = set()

    for valor in raw.split(","):
        valor = valor.strip()

        if valor.isdigit():
            admins.add(int(valor))

    return admins


def _fecha_legible(valor):
    if not valor:
        return "fecha desconocida"

    try:
        fecha = datetime.fromisoformat(
            str(valor).replace("Z", "+00:00")
        )
        return fecha.strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(valor)


def _linea_usuario(numero, usuario):
    nombre = " ".join(
        str(usuario.get("nombre") or "Sin nombre").split()
    )

    username = usuario.get("username")
    etiqueta = f" (@{username})" if username else ""

    fecha = _fecha_legible(usuario.get("creado_en"))

    return (
        f"{numero}. {nombre}{etiqueta}\n"
        f"   ID: {usuario['user_id']} | Registro: {fecha}"
    )


async def users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message
    user = update.effective_user

    if not mensaje or not user:
        return

    admins = _admins_configurados()

    if not admins:
        await mensaje.reply_text(
            "⚠️ No se ha configurado ningún administrador.\n"
            "Configura tu ID numérico en la variable ADMIN_IDS "
            "de Railway."
        )
        return

    if user.id not in admins:
        await mensaje.reply_text(
            "⛔ No tienes permiso para usar este comando."
        )
        return

    usuarios = listar_usuarios()
    total = len(usuarios)

    if total == 0:
        await mensaje.reply_text(
            "👥 Todavía no hay usuarios registrados."
        )
        return

    encabezado = (
        "👥 USUARIOS DE TRIVIA DE QUÍMICA\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"Total registrados: {total}\n"
        "Orden: del más antiguo al más reciente\n\n"
    )

    mensajes = []
    actual = encabezado

    for numero, usuario in enumerate(usuarios, start=1):
        linea = _linea_usuario(numero, usuario) + "\n\n"

        if len(actual) + len(linea) > LIMITE_MENSAJE:
            mensajes.append(actual.rstrip())
            actual = (
                "👥 USUARIOS — CONTINUACIÓN\n"
                f"Total registrados: {total}\n\n"
            )

        actual += linea

    if actual.strip():
        mensajes.append(actual.rstrip())

    for bloque in mensajes:
        await mensaje.reply_text(bloque)
