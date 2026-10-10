# juegos/desafio_sustancias.py

import random
import time
import unicodedata

from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

from juegos.sustancias import SUSTANCIAS
from core.db import sumar_xp


XP_POR_ACIERTO = 100
COOLDOWN_SEGUNDOS = 60

DESAFIOS_ACTIVOS = {}
COOLDOWNS = {}


def normalizar_nombre(texto):
    """Ignora mayúsculas, acentos y espacios sobrantes."""
    texto = texto.strip().casefold()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(texto.split())


def normalizar_formula(texto):
    """
    Convierte subíndices a números normales.
    Mantiene las mayúsculas y minúsculas de los símbolos químicos.
    """
    traduccion = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    return texto.strip().translate(traduccion)


def obtener_tiempo_limite(formula):
    longitud = len(formula)

    if longitud <= 4:
        return 10
    elif longitud <= 8:
        return 20
    return 30


def obtener_catalogo():
    """
    Admite el catálogo como lista de diccionarios o lista de tuplas:
    (formula, nombre, descripcion1, descripcion2).
    """
    catalogo = []

    for item in SUSTANCIAS:
        try:
            if isinstance(item, dict):
                formula = item.get("formula") or item.get("formula_quimica")
                nombre = item.get("nombre")
            else:
                formula = item[0]
                nombre = item[1]

            if formula and nombre:
                catalogo.append({
                    "formula": str(formula).strip(),
                    "nombre": str(nombre).strip(),
                })
        except (IndexError, KeyError, TypeError):
            continue

    return catalogo


def tiempo_restante(user_id):
    fin = COOLDOWNS.get(user_id, 0)
    return max(0, int(fin - time.monotonic() + 0.999))


def activar_cooldown(user_id):
    COOLDOWNS[user_id] = time.monotonic() + COOLDOWN_SEGUNDOS


def cancelar_temporizador(context, user_id):
    if context.job_queue is None:
        return

    nombre_job = f"desafio_sustancias_{user_id}"

    for job in context.job_queue.get_jobs_by_name(nombre_job):
        job.schedule_removal()


async def terminar_desafio(
    context,
    user_id,
    motivo,
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
        texto = (
            "❌ ¡Respuesta incorrecta!\n\n"
            f"Tu respuesta: {respuesta_usuario}\n"
            f"Respuesta correcta: "
            f"{formula if desafio['tipo'] == 'formula' else nombre}\n\n"
            f"🧪 Sustancia: {nombre}\n"
            f"⚗️ Fórmula: {formula}\n"
            "🏁 El desafío ha terminado. No ganas XP."
        )

    texto += "\n⏳ Podrás jugar otra vez dentro de 60 segundos."

    await context.bot.send_message(
        chat_id=desafio["chat_id"],
        text=texto,
    )


async def temporizador_desafio(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]

    await terminar_desafio(
        context,
        user_id,
        motivo="tiempo",
    )


async def comenzar_desafio(update, context):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    user_id = user.id

    restante = tiempo_restante(user_id)
    if restante > 0:
        await message.reply_text(
            f"⏳ Espera {restante} segundos antes de jugar otra vez."
        )
        return

    if user_id in DESAFIOS_ACTIVOS:
        await message.reply_text(
            "🧪 Ya tienes un desafío activo. "
            "Responde antes de que termine el tiempo."
        )
        return

    catalogo = obtener_catalogo()

    if not catalogo:
        await message.reply_text(
            "❌ No se encontraron sustancias en SUSTANCIAS. "
            "Comprueba el formato del catálogo."
        )
        return

    sustancia = random.choice(catalogo)
    formula = sustancia["formula"]
    nombre = sustancia["nombre"]

    limite = obtener_tiempo_limite(formula)

    # Dos tipos de pregunta:
    # 1. Nombre -> el usuario debe responder la fórmula.
    # 2. Fórmula -> el usuario debe responder el nombre.
    tipo = random.choice(("formula", "nombre"))

    if tipo == "formula":
        pregunta = (
            "🧪 DESAFÍO DE QUÍMICA\n\n"
            f"¿Cuál es la fórmula química de {nombre}?\n\n"
            f"⏱️ Tienes {limite} segundos.\n"
            f"🏆 Si aciertas, ganas {XP_POR_ACIERTO} XP.\n"
            "✍️ Responde escribiendo solamente la fórmula."
        )
    else:
        pregunta = (
            "🧪 DESAFÍO DE QUÍMICA\n\n"
            f"¿Qué sustancia corresponde a la fórmula {formula}?\n\n"
            f"⏱️ Tienes {limite} segundos.\n"
            f"🏆 Si aciertas, ganas {XP_POR_ACIERTO} XP.\n"
            "✍️ Responde escribiendo solamente el nombre."
        )

    DESAFIOS_ACTIVOS[user_id] = {
        "sustancia": sustancia,
        "tipo": tipo,
        "chat_id": update.effective_chat.id,
    }

    await message.reply_text(pregunta)

    if context.job_queue is None:
        DESAFIOS_ACTIVOS.pop(user_id, None)
        await message.reply_text(
            "❌ Falta activar JobQueue. Instala "
            "`python-telegram-bot[job-queue]`."
        )
        return

    context.job_queue.run_once(
        temporizador_desafio,
        when=limite,
        data={"user_id": user_id},
        name=f"desafio_sustancias_{user_id}",
    )


async def constructor_desafio(update, context):
    """
    Handler para /constructor desafio.
    """
    args = context.args or []

    if not args or args[0].casefold() != "desafio":
        return

    await comenzar_desafio(update, context)


async def responder_desafio(update, context):
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.text:
        return

    user_id = user.id
    desafio = DESAFIOS_ACTIVOS.get(user_id)

    if not desafio:
        return

    if message.chat_id != desafio["chat_id"]:
        return

    # Solo texto normal. Los comandos como /agua no se aceptan.
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

    # Cualquier error termina el desafío.
    if not correcto:
        await terminar_desafio(
            context,
            user_id,
            motivo="error",
            respuesta_usuario=message.text,
        )
        return

    # Se retira primero el desafío para impedir respuestas duplicadas.
    DESAFIOS_ACTIVOS.pop(user_id, None)
    cancelar_temporizador(context, user_id)
    activar_cooldown(user_id)

    try:
        resultado = sumar_xp(user_id, XP_POR_ACIERTO)

        if hasattr(resultado, "__await__"):
            await resultado

        await message.reply_text(
            "✅ ¡Correcto!\n\n"
            f"🧪 {nombre_correcto}\n"
            f"⚗️ Fórmula: {formula_correcta}\n"
            f"🏆 +{XP_POR_ACIERTO} XP\n\n"
            "🎉 ¡Desafío superado!\n"
            "⏳ Podrás jugar otra vez dentro de 60 segundos."
        )

    except Exception as error:
        print(f"[Desafío de sustancias] Error al dar XP: {error}")

        await message.reply_text(
            "✅ ¡Respuesta correcta!\n"
            f"🧪 {nombre_correcto} — {formula_correcta}\n"
            "⚠️ No se pudo guardar la XP. "
            "Comprueba la firma de core.db.sumar_xp."
        )


def registrar_desafio_sustancias(application):
    """
    Registra los handlers si /constructor no está registrado todavía.

    Si ya existe un handler /constructor, integra la llamada a
    constructor_desafio en ese handler y registra solo responder_desafio.
    """
    application.add_handler(
        CommandHandler("constructor", constructor_desafio),
        group=10,
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder_desafio,
        ),
        group=11,
    )