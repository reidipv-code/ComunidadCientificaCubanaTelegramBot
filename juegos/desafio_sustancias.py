import random
import time
import unicodedata

from telegram import Update
from telegram.ext import ContextTypes

from core.profile_db import agregar_xp, registrar_usuario
from juegos.sustancias import SUSTANCIAS


XP_POR_ACIERTO = 100
COOLDOWN_SEGUNDOS = 60

DESAFIOS_ACTIVOS = {}
COOLDOWNS = {}


def normalizar_nombre(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.strip().casefold())
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(texto.split())


def normalizar_formula(texto: str) -> str:
    traduccion = str.maketrans(
        "₀₁₂₃₄₅₆₇₈₉",
        "0123456789",
    )
    return texto.strip().translate(traduccion)


def obtener_tiempo_limite(formula: str) -> int:
    longitud = len(formula)

    if longitud <= 4:
        return 10
    if longitud <= 8:
        return 20
    return 30


def obtener_catalogo():
    catalogo = []

    for item in SUSTANCIAS:
        if not isinstance(item, dict):
            continue

        formula = item.get("formula")
        nombre = item.get("nombre")

        if formula and nombre:
            catalogo.append({
                "formula": str(formula).strip(),
                "nombre": str(nombre).strip(),
            })

    return catalogo


def tiempo_restante(user_id: int) -> int:
    fin = COOLDOWNS.get(user_id, 0)
    return max(0, int(fin - time.monotonic() + 0.999))


def activar_cooldown(user_id: int):
    COOLDOWNS[user_id] = (
        time.monotonic() + COOLDOWN_SEGUNDOS
    )


def cancelar_temporizador(context, user_id: int):
    if context.job_queue is None:
        return

    nombre_job = f"desafio_sustancias_{user_id}"

    for job in context.job_queue.get_jobs_by_name(nombre_job):
        job.schedule_removal()


async def terminar_desafio(
    context,
    user_id: int,
    motivo: str,
    respuesta_usuario=None,
):
    desafio = DESAFIOS_ACTIVOS.pop(user_id, None)

    if not desafio:
        return

    cancelar_temporizador(context, user_id)
    activar_cooldown(user_id)

    sustancia = desafio["sustancia"]
    nombre = sustancia["nombre"]
    formula = sustancia["formula"]

    if motivo == "tiempo":
        texto = (
            "⏰ ¡Se acabó el tiempo!\n\n"
            f"🧪 Sustancia: {nombre}\n"
            f"⚗️ Fórmula: {formula}\n"
            "❌ Desafío perdido. No ganas XP."
        )
    else:
        correcta = (
            formula
            if desafio["tipo"] == "formula"
            else nombre
        )

        texto = (
            "❌ ¡Respuesta incorrecta!\n\n"
            f"Tu respuesta: {respuesta_usuario}\n"
            f"Respuesta correcta: {correcta}\n\n"
            f"🧪 Sustancia: {nombre}\n"
            f"⚗️ Fórmula: {formula}\n"
            "🏁 Desafío terminado. No ganas XP."
        )

    texto += (
        "\n\n⏳ Podrás jugar otra vez "
        "dentro de 60 segundos."
    )

    await context.bot.send_message(
        chat_id=desafio["chat_id"],
        text=texto,
    )


async def temporizador_desafio(context: ContextTypes.DEFAULT_TYPE):
    job = context.job

    if not job or not job.data:
        return

    await terminar_desafio(
        context,
        job.data["user_id"],
        motivo="tiempo",
    )


async def comenzar_desafio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat

    if not user or not message or not chat:
        return

    if context.job_queue is None:
        await message.reply_text(
            '❌ JobQueue no disponible. Instala '
            '"python-telegram-bot[job-queue]".'
        )
        return

    restante = tiempo_restante(user.id)

    if restante > 0:
        await message.reply_text(
            f"⏳ Espera {restante} segundos "
            "antes de jugar otra vez."
        )
        return

    if user.id in DESAFIOS_ACTIVOS:
        await message.reply_text(
            "🧪 Ya tienes un desafío activo. "
            "Responde antes de que termine el tiempo."
        )
        return

    catalogo = obtener_catalogo()

    if not catalogo:
        await message.reply_text(
            "❌ No se encontraron sustancias en "
            "juegos/sustancias.py."
        )
        return

    sustancia = random.choice(catalogo)
    formula = sustancia["formula"]
    nombre = sustancia["nombre"]

    limite = obtener_tiempo_limite(formula)
    tipo = random.choice(("formula", "nombre"))

    if tipo == "formula":
        pregunta = (
            "🧪 DESAFÍO DE QUÍMICA\n\n"
            f"¿Cuál es la fórmula química de {nombre}?\n\n"
            f"⏱️ Tienes {limite} segundos.\n"
            f"🏆 Ganas {XP_POR_ACIERTO} XP si aciertas.\n"
            "✍️ Escribe solamente la fórmula."
        )
    else:
        pregunta = (
            "🧪 DESAFÍO DE QUÍMICA\n\n"
            f"¿Qué sustancia corresponde a {formula}?\n\n"
            f"⏱️ Tienes {limite} segundos.\n"
            f"🏆 Ganas {XP_POR_ACIERTO} XP si aciertas.\n"
            "✍️ Escribe solamente el nombre."
        )

    DESAFIOS_ACTIVOS[user.id] = {
        "sustancia": sustancia,
        "tipo": tipo,
        "chat_id": chat.id,
    }

    try:
        context.job_queue.run_once(
            temporizador_desafio,
            when=limite,
            data={"user_id": user.id},
            name=f"desafio_sustancias_{user.id}",
        )
    except Exception:
        DESAFIOS_ACTIVOS.pop(user.id, None)
        await message.reply_text(
            "❌ No pude iniciar el temporizador."
        )
        raise

    await message.reply_text(pregunta)


async def responder_desafio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.text:
        return

    desafio = DESAFIOS_ACTIVOS.get(user.id)

    if not desafio:
        return

    if message.chat_id != desafio["chat_id"]:
        return

    if message.text.startswith(("/", ".")):
        return

    sustancia = desafio["sustancia"]
    formula_correcta = sustancia["formula"]
    nombre_correcto = sustancia["nombre"]

    if desafio["tipo"] == "formula":
        correcto = (
            normalizar_formula(message.text)
            == normalizar_formula(formula_correcta)
        )
    else:
        correcto = (
            normalizar_nombre(message.text)
            == normalizar_nombre(nombre_correcto)
        )

    if not correcto:
        await terminar_desafio(
            context,
            user.id,
            motivo="error",
            respuesta_usuario=message.text,
        )
        return

    # Eliminar primero el desafío evita entregar XP dos veces.
    DESAFIOS_ACTIVOS.pop(user.id, None)
    cancelar_temporizador(context, user.id)
    activar_cooldown(user.id)

    try:
        registrar_usuario(
            user.id,
            user.full_name or user.username or f"Jugador {user.id}",
            user.username,
        )

        agregar_xp(user.id, XP_POR_ACIERTO)

    except Exception:
        await message.reply_text(
            "✅ ¡Respuesta correcta!\n"
            f"🧪 {nombre_correcto} — {formula_correcta}\n"
            "⚠️ No se pudo guardar la XP. "
            "Revisa los logs del bot."
        )
        return

    await message.reply_text(
        "✅ ¡Correcto!\n\n"
        f"🧪 {nombre_correcto}\n"
        f"⚗️ Fórmula: {formula_correcta}\n"
        f"🏆 +{XP_POR_ACIERTO} XP\n\n"
        "🎉 ¡Desafío superado!\n"
        "⏳ Podrás jugar otra vez dentro de 60 segundos."
    )