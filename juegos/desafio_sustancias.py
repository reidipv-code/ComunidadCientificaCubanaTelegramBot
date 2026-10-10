import random
import time
import unicodedata

from telegram import Update
from telegram.ext import ContextTypes

from core.profile_db import agregar_xp, registrar_usuario
from juegos.sustancias import SUSTANCIAS


XP_POR_ACIERTO = 5
COOLDOWN_SEGUNDOS = 60

DESAFIOS_ACTIVOS = {}
COOLDOWNS = {}


def normalizar_nombre(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.strip().casefold())

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
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

        if not formula or not nombre:
            continue

        catalogo.append({
            "formula": str(formula).strip(),
            "nombre": str(nombre).strip(),
        })

    return catalogo


def tiempo_restante(user_id: int) -> int:
    fin = COOLDOWNS.get(user_id, 0)

    return max(
        0,
        int(fin - time.monotonic() + 0.999),
    )


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

    if desafio is None:
        return

    cancelar_temporizador(context, user_id)
    activar_cooldown(user_id)

    sustancia = desafio["sustancia"]

    nombre = sustancia["nombre"]
    formula = sustancia["formula"]

    if motivo == "tiempo":
        texto = (
            "⏰ ¡SE ACABÓ EL TIEMPO!\n\n"
            f"🧪 Sustancia: {nombre}\n"
            f"⚗️ Fórmula: {formula}\n\n"
            "❌ Has perdido la partida."
        )

    elif motivo == "error":
        correcta = (
            formula
            if desafio["tipo"] == "formula"
            else nombre
        )

        texto = (
            "❌ ¡RESPUESTA INCORRECTA!\n\n"
            f"✍️ Tu respuesta: {respuesta_usuario}\n"
            f"✅ Respuesta correcta: {correcta}\n\n"
            f"🧪 Sustancia: {nombre}\n"
            f"⚗️ Fórmula: {formula}\n\n"
            "🏁 ¡La partida ha terminado!"
        )

    else:
        texto = (
            "⚠️ La partida ha terminado por un error interno."
        )

    texto += (
        f"\n\n🏆 EXP obtenida durante la partida: "
        f"{desafio['xp_ganada']}\n"
        "⏳ Podrás jugar otra vez dentro de 60 segundos."
    )

    await context.bot.send_message(
        chat_id=desafio["chat_id"],
        text=texto,
    )


async def temporizador_desafio(
    context: ContextTypes.DEFAULT_TYPE,
):
    job = context.job

    if job is None or not job.data:
        return

    user_id = job.data["user_id"]
    pregunta_id = job.data["pregunta_id"]

    desafio = DESAFIOS_ACTIVOS.get(user_id)

    if desafio is None:
        return

    # Ignorar temporizadores pertenecientes a preguntas anteriores.
    if desafio["pregunta_id"] != pregunta_id:
        return

    limite_final = desafio.get("limite_final")

    if limite_final is None:
        return

    restante = limite_final - time.monotonic()

    # Si el programador ejecuta el callback ligeramente antes,
    # volver a programarlo para el tiempo restante.
    if restante > 0:
        context.job_queue.run_once(
            temporizador_desafio,
            when=restante,
            data={
                "user_id": user_id,
                "pregunta_id": pregunta_id,
            },
            name=f"desafio_sustancias_{user_id}",
        )
        return

    await terminar_desafio(
        context,
        user_id,
        motivo="tiempo",
    )


async def enviar_pregunta(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    sustancia_anterior=None,
):
    desafio = DESAFIOS_ACTIVOS.get(user_id)

    if desafio is None:
        return

    catalogo = desafio["catalogo"]

    if not catalogo:
        DESAFIOS_ACTIVOS.pop(user_id, None)

        await update.effective_message.reply_text(
            "❌ No hay sustancias disponibles para jugar."
        )
        return

    opciones = [
        item
        for item in catalogo
        if item["formula"] != sustancia_anterior
    ]

    if not opciones:
        opciones = catalogo

    sustancia = random.choice(opciones)

    formula = sustancia["formula"]
    nombre = sustancia["nombre"]

    limite = obtener_tiempo_limite(formula)
    tipo = random.choice(("formula", "nombre"))

    desafio["sustancia"] = sustancia
    desafio["tipo"] = tipo
    desafio["pregunta_id"] += 1

    pregunta_id = desafio["pregunta_id"]

    # Invalidar cualquier plazo anterior.
    desafio["limite_final"] = None

    if tipo == "formula":
        pregunta = (
            "🧪 DESAFÍO INFINITO DE QUÍMICA\n\n"
            f"¿Cuál es la fórmula química de {nombre}?\n\n"
            f"⏱️ Tiempo para responder: {limite} segundos\n"
            f"⭐ Recompensa por acertar: +{XP_POR_ACIERTO} EXP\n"
            f"🏆 EXP acumulada en esta partida: "
            f"{desafio['xp_ganada']}\n\n"
            "✍️ Escribe solamente la fórmula.\n"
            "♾️ ¡Cada acierto te dará otra pregunta!"
        )

    else:
        pregunta = (
            "🧪 DESAFÍO INFINITO DE QUÍMICA\n\n"
            f"¿Qué sustancia corresponde a {formula}?\n\n"
            f"⏱️ Tiempo para responder: {limite} segundos\n"
            f"⭐ Recompensa por acertar: +{XP_POR_ACIERTO} EXP\n"
            f"🏆 EXP acumulada en esta partida: "
            f"{desafio['xp_ganada']}\n\n"
            "✍️ Escribe solamente el nombre.\n"
            "♾️ ¡Cada acierto te dará otra pregunta!"
        )

    try:
        # Primero enviar la pregunta.
        await update.effective_message.reply_text(pregunta)

        # El cronómetro empieza después de que Telegram
        # confirma el envío del mensaje.
        limite_final = time.monotonic() + limite

        desafio["limite_final"] = limite_final

        context.job_queue.run_once(
            temporizador_desafio,
            when=limite,
            data={
                "user_id": user_id,
                "pregunta_id": pregunta_id,
            },
            name=f"desafio_sustancias_{user_id}",
        )

    except Exception:
        cancelar_temporizador(context, user_id)

        desafio_actual = DESAFIOS_ACTIVOS.get(user_id)

        if desafio_actual is desafio:
            DESAFIOS_ACTIVOS.pop(user_id, None)

        raise


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

    if user.id in DESAFIOS_ACTIVOS:
        await message.reply_text(
            "🧪 Ya tienes una partida activa.\n"
            "♾️ ¡Sigue respondiendo para ganar EXP!"
        )
        return

    restante = tiempo_restante(user.id)

    if restante > 0:
        await message.reply_text(
            f"⏳ Espera {restante} segundos "
            "antes de comenzar otra partida."
        )
        return

    catalogo = obtener_catalogo()

    if not catalogo:
        await message.reply_text(
            "❌ No se encontraron sustancias en "
            "juegos/sustancias.py."
        )
        return

    DESAFIOS_ACTIVOS[user.id] = {
        "chat_id": chat.id,
        "catalogo": catalogo,
        "sustancia": None,
        "tipo": None,
        "pregunta_id": 0,
        "xp_ganada": 0,
        "limite_final": None,
    }

    await enviar_pregunta(
        update,
        context,
        user.id,
    )


async def responder_desafio(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.text:
        return

    desafio = DESAFIOS_ACTIVOS.get(user.id)

    if desafio is None:
        return

    if message.chat_id != desafio["chat_id"]:
        return

    if message.text.startswith(("/", ".")):
        return

    sustancia = desafio["sustancia"]

    if sustancia is None:
        return

    limite_final = desafio.get("limite_final")

    # Comprobar el plazo real al recibir la respuesta.
    # Así no se aceptan respuestas enviadas después del límite,
    # aunque el callback del temporizador se haya retrasado.
    if (
        limite_final is not None
        and time.monotonic() >= limite_final
    ):
        await terminar_desafio(
            context,
            user.id,
            motivo="tiempo",
        )
        return

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

    # Guardar la fórmula anterior para evitar repetir
    # inmediatamente la misma sustancia.
    sustancia_anterior = formula_correcta

    # Cancelar el cronómetro de la pregunta respondida.
    cancelar_temporizador(context, user.id)

    # Invalidar el plazo mientras se procesa el acierto.
    desafio["limite_final"] = None

    try:
        registrar_usuario(
            user.id,
            user.full_name or user.username or f"Jugador {user.id}",
            user.username,
        )

        agregar_xp(user.id, XP_POR_ACIERTO)

    except Exception:
        await terminar_desafio(
            context,
            user.id,
            motivo="sistema",
        )

        await message.reply_text(
            "⚠️ No se pudo guardar la EXP. "
            "Revisa los logs del bot."
        )
        return

    desafio["xp_ganada"] += XP_POR_ACIERTO

    await message.reply_text(
        "✅ ¡RESPUESTA CORRECTA!\n\n"
        f"🧪 {nombre_correcto}\n"
        f"⚗️ Fórmula: {formula_correcta}\n"
        f"⭐ +{XP_POR_ACIERTO} EXP\n"
        f"🏆 EXP ganada en esta partida: "
        f"{desafio['xp_ganada']}\n\n"
        "♾️ ¡La partida continúa!"
    )

    # No hay límite de preguntas ni premio final:
    # cada respuesta correcta da exactamente 5 EXP.
    await enviar_pregunta(
        update,
        context,
        user.id,
        sustancia_anterior=sustancia_anterior,
    )