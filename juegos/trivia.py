import random
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError

from core.xp_client import consultar_usuario, otorgar_xp, XPAPIError
from juegos.preguntas import obtener_preguntas


TOTAL_PREGUNTAS = 10
VIDAS_INICIALES = 3
TIEMPO_PREGUNTA = 10
COOLDOWN_PERDIDA = 90
RETRASO_SIGUIENTE = 1.25

LETRAS = ("A", "B", "C", "D")


def _partidas(application):
    return application.bot_data.setdefault("trivia_partidas", {})


def _cooldowns(application):
    return application.bot_data.setdefault("trivia_cooldowns", {})


def _cancelar_timeout(partida):
    job = partida.get("timeout_job")
    if job:
        job.schedule_removal()
        partida["timeout_job"] = None


def _corazones(vidas):
    return "❤️" * max(0, vidas) + "🖤" * max(0, VIDAS_INICIALES - vidas)


def _texto_pregunta(partida):
    pregunta = partida["preguntas"][partida["indice"]]
    grados = " y ".join(str(g) for g in partida["grados"])
    return (
        "🧪 TRIVIA DE QUÍMICA\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🎓 Grado(s): {grados}\n"
        f"❓ Pregunta {partida['indice'] + 1}/{TOTAL_PREGUNTAS}\n"
        f"💗 Vidas: {_corazones(partida['vidas'])}\n"
        f"⏱️ Tienes {TIEMPO_PREGUNTA} segundos\n\n"
        f"{pregunta['prompt']}"
    )


def _teclado(partida):
    botones = []
    opciones = partida["opciones_actuales"]
    for i in range(0, 4, 2):
        fila = []
        for j in range(i, i + 2):
            texto = opciones[j]["text"].replace("\n", " ").strip()
            etiqueta = f"{LETRAS[j]}) {texto}"
            if len(etiqueta) > 58:
                etiqueta = etiqueta[:55] + "..."
            fila.append(
                InlineKeyboardButton(
                    etiqueta,
                    callback_data=f"qt|{partida['sid']}|{j}",
                )
            )
        botones.append(fila)
    return InlineKeyboardMarkup(botones)


async def _mostrar_pregunta(context, partida):
    if partida["indice"] >= TOTAL_PREGUNTAS:
        await _finalizar_ganada(context, partida)
        return

    pregunta = partida["preguntas"][partida["indice"]]
    opciones = [dict(op) for op in pregunta["options"]]
    random.shuffle(opciones)
    partida["opciones_actuales"] = opciones
    partida["respondida"] = False

    try:
        await context.bot.edit_message_text(
            chat_id=partida["chat_id"],
            message_id=partida["message_id"],
            text=_texto_pregunta(partida),
            reply_markup=_teclado(partida),
        )
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise

    partida["timeout_job"] = context.job_queue.run_once(
        _timeout_pregunta,
        TIEMPO_PREGUNTA,
        data={"user_id": partida["user_id"], "sid": partida["sid"]},
        name=f"trivia_timeout_{partida['sid']}",
    )


async def _programar_siguiente(context, partida):
    context.job_queue.run_once(
        _avanzar_pregunta,
        RETRASO_SIGUIENTE,
        data={"user_id": partida["user_id"], "sid": partida["sid"]},
        name=f"trivia_next_{partida['sid']}",
    )


async def _avanzar_pregunta(context):
    data = context.job.data
    partida = _partidas(context.application).get(data["user_id"])
    if not partida or partida["sid"] != data["sid"]:
        return
    partida["indice"] += 1
    if partida["indice"] >= TOTAL_PREGUNTAS:
        await _finalizar_ganada(context, partida)
        return
    await _mostrar_pregunta(context, partida)


async def _timeout_pregunta(context):
    data = context.job.data
    partida = _partidas(context.application).get(data["user_id"])
    if not partida or partida["sid"] != data["sid"] or partida["respondida"]:
        return

    partida["respondida"] = True
    partida["timeout_job"] = None
    partida["vidas"] -= 1

    pregunta = partida["preguntas"][partida["indice"]]
    correcta = next(op["text"] for op in pregunta["options"] if op["correct"])
    texto = (
        f"⌛ Se acabó el tiempo.\n"
        f"❌ Perdiste una vida.\n"
        f"✅ Respuesta correcta: {correcta}\n\n"
        f"💗 Vidas: {_corazones(partida['vidas'])}"
    )
    if partida["vidas"] <= 0:
        await _finalizar_perdida(context, partida, texto)
        return

    await context.bot.edit_message_text(
        chat_id=partida["chat_id"],
        message_id=partida["message_id"],
        text=texto,
    )
    await _programar_siguiente(context, partida)


async def responder_boton(update, context):
    query = update.callback_query
    await query.answer()

    try:
        prefijo, sid, indice_txt = query.data.split("|", 2)
        indice_opcion = int(indice_txt)
    except (ValueError, AttributeError):
        return

    if prefijo != "qt":
        return

    user_id = query.from_user.id
    partida = _partidas(context.application).get(user_id)
    if not partida or partida["sid"] != sid:
        await query.answer("Esta partida ya terminó.", show_alert=True)
        return

    if query.message.chat_id != partida["chat_id"]:
        await query.answer("Este botón pertenece a otra partida.", show_alert=True)
        return

    if partida["respondida"]:
        return

    if not 0 <= indice_opcion < len(partida["opciones_actuales"]):
        return

    partida["respondida"] = True
    _cancelar_timeout(partida)

    opcion_elegida = partida["opciones_actuales"][indice_opcion]
    pregunta = partida["preguntas"][partida["indice"]]

    if opcion_elegida["correct"]:
        partida["aciertos"] += 1
        texto = (
            "✅ ¡Correcto!\n\n"
            f"💗 Vidas: {_corazones(partida['vidas'])}\n"
            f"🎯 Aciertos: {partida['aciertos']}"
        )
    else:
        partida["vidas"] -= 1
        correcta = next(op["text"] for op in pregunta["options"] if op["correct"])
        texto = (
            "❌ Esa respuesta es incorrecta.\n"
            f"✅ Respuesta correcta: {correcta}\n"
            "💔 Perdiste una vida.\n\n"
            f"💗 Vidas: {_corazones(partida['vidas'])}\n"
            f"🎯 Aciertos: {partida['aciertos']}"
        )

    if partida["vidas"] <= 0:
        await _finalizar_perdida(context, partida, texto)
        return

    await query.edit_message_text(text=texto)
    await _programar_siguiente(context, partida)


async def _finalizar_perdida(context, partida, mensaje_previo=None):
    _cancelar_timeout(partida)
    _partidas(context.application).pop(partida["user_id"], None)
    _cooldowns(context.application)[partida["user_id"]] = time.time() + COOLDOWN_PERDIDA

    texto = (
        "💀 PARTIDA PERDIDA\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Te quedaste sin vidas. No ganaste EXP.\n"
        "⏳ Podrás jugar otra vez dentro de 1 minuto y 30 segundos."
    )
    if mensaje_previo:
        texto = mensaje_previo + "\n\n" + texto

    try:
        await context.bot.edit_message_text(
            chat_id=partida["chat_id"],
            message_id=partida["message_id"],
            text=texto,
        )
    except TelegramError:
        pass


async def _finalizar_ganada(context, partida):
    _cancelar_timeout(partida)
    user_id = partida["user_id"]
    vidas = partida["vidas"]
    recompensa = {3: 100, 2: 50, 1: 25}.get(vidas, 0)

    if recompensa <= 0:
        await _finalizar_perdida(context, partida)
        return

    try:
        resultado = await otorgar_xp(
            user_id=user_id,
            cantidad=recompensa,
            request_id=f"quimica-{partida['sid']}-{user_id}",
        )
    except XPAPIError as exc:
        _partidas(context.application).pop(user_id, None)
        try:
            await context.bot.edit_message_text(
                chat_id=partida["chat_id"],
                message_id=partida["message_id"],
                text=(
                    "🏁 ¡Terminaste las 10 preguntas!\n"
                    f"🎯 Aciertos: {partida['aciertos']}/10\n"
                    "⚠️ No pude registrar la EXP compartida con ReidiStudiosBot.\n"
                    "El administrador debe revisar XP_API_URL y XP_API_TOKEN.\n"
                    f"Detalle: {str(exc)[:250]}"
                ),
            )
        except TelegramError:
            pass
        return

    _partidas(context.application).pop(user_id, None)
    texto = (
        "🏆 ¡PARTIDA COMPLETADA!\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Aciertos: {partida['aciertos']}/10\n"
        f"💗 Vidas restantes: {_corazones(vidas)}\n"
        f"⭐ Recompensa: +{recompensa} EXP\n"
        "✅ EXP añadida a tu cuenta de ReidiStudiosBot."
    )
    if resultado.get("leveled_up"):
        texto += f"\n🎉 ¡Subiste al nivel {resultado.get('nivel')}!"
    try:
        await context.bot.edit_message_text(
            chat_id=partida["chat_id"],
            message_id=partida["message_id"],
            text=texto,
        )
    except TelegramError:
        pass


async def iniciar_partida(update, context, grados):
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not update.effective_message:
        return

    partidas = _partidas(context.application)
    if user.id in partidas:
        await update.effective_message.reply_text(
            "⚠️ Ya tienes una partida de Química en curso. Termínala primero."
        )
        return

    ahora = time.time()
    fin_cooldown = _cooldowns(context.application).get(user.id, 0)
    if ahora < fin_cooldown:
        restante = int(fin_cooldown - ahora + 0.999)
        await update.effective_message.reply_text(
            f"⏳ Espera {restante} segundos antes de iniciar otra partida."
        )
        return

    try:
        registrado = await consultar_usuario(user.id)
    except XPAPIError as exc:
        await update.effective_message.reply_text(
            "⚠️ No puedo conectar con ReidiStudiosBot para comprobar tu registro.\n"
            "La integración de EXP compartida debe estar configurada.\n\n"
            f"Detalle: {str(exc)[:250]}"
        )
        return

    if not registrado:
        await update.effective_message.reply_text(
            "🔒 Primero debes registrarte en ReidiStudiosBot con /reg nombre.pais."
        )
        return

    banco = obtener_preguntas(grados)
    if len(banco) < TOTAL_PREGUNTAS:
        await update.effective_message.reply_text(
            f"❌ No hay suficientes preguntas para los grados {', '.join(map(str, grados))}."
        )
        return

    seleccion = random.sample(banco, TOTAL_PREGUNTAS)
    sid = f"{random.getrandbits(32):08x}"
    partida = {
        "sid": sid,
        "user_id": user.id,
        "chat_id": chat.id,
        "message_id": None,
        "grados": grados,
        "preguntas": seleccion,
        "indice": 0,
        "vidas": VIDAS_INICIALES,
        "aciertos": 0,
        "opciones_actuales": [],
        "respondida": False,
        "timeout_job": None,
    }

    mensaje = await update.effective_message.reply_text("🧪 Preparando tu partida...")
    partida["message_id"] = mensaje.message_id
    partidas[user.id] = partida

    try:
        await _mostrar_pregunta(context, partida)
    except TelegramError:
        partidas.pop(user.id, None)
        raise
