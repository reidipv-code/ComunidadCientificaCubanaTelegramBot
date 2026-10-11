# comandos/constructor.py

import unicodedata

from telegram import Update
from telegram.ext import ContextTypes

from core.constructor_db import (
    listar_descubrimientos,
    registrar_descubrimiento,
    usuario_descubrio_nombre,
)
from juegos.sustancias import SUSTANCIAS
from juegos.desafio_sustancias import comenzar_desafio


SUBINDICES = str.maketrans(
    "₀₁₂₃₄₅₆₇₈₉",
    "0123456789",
)


def _formula_normalizada(texto: str) -> str:
    return texto.translate(SUBINDICES).strip()


def _nombre_normalizado(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto.strip())
    return texto.casefold()


def _buscar_por_formula(formula: str):
    formula = _formula_normalizada(formula)

    return [
        sustancia
        for sustancia in SUSTANCIAS
        if _formula_normalizada(sustancia["formula"]) == formula
    ]


def _buscar_por_nombre(nombre: str):
    buscado = _nombre_normalizado(nombre)

    return [
        sustancia
        for sustancia in SUSTANCIAS
        if _nombre_normalizado(sustancia["nombre"]) == buscado
    ]


def _texto_sustancia(sustancia: dict) -> str:
    return (
        f"🧪 {sustancia['nombre']}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛠️ {sustancia['descripcion1']}\n\n"
        f"💡 {sustancia['descripcion2']}\n\n"
        f"⚗️ Fórmula: {sustancia['formula']}"
    )


async def constructor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message
    usuario = update.effective_user

    if not mensaje or not usuario:
        return

    if not context.args:
        await mensaje.reply_text(
            "🧪 CONSTRUCTOR DE SUSTANCIAS\n\n"
            "🔬 Descubre sustancias con su fórmula:\n"
            "/constructor H2O\n\n"
            "📖 Consulta una sustancia descubierta:\n"
            "/constructor agua\n\n"
            "📚 Consulta tus descubrimientos:\n"
            "/constructor lista de sustancias\n\n"
            "🎮 Desafío de química:\n"
            "/constructor desafio\n\n"
            "En el desafío debes responder dentro del tiempo "
            "para ganar 100 EXP."
        )
        return

    argumento = " ".join(context.args).strip()
    argumento_normalizado = _nombre_normalizado(argumento)

    # ==================== DESAFÍO ====================

    if argumento_normalizado in {
        "desafio",
        "desafío",
        "reto",
        "challenge",
    }:
        await comenzar_desafio(update, context)
        return

    # ==================== LISTA DE SUSTANCIAS ====================

    if argumento_normalizado in {
        "lista de sustancias",
        "lista sustancias",
        "mis sustancias",
    }:
        descubrimientos = listar_descubrimientos(usuario.id)

        # El total se calcula directamente desde el catálogo.
        # Si se agregan o eliminan sustancias, se actualiza solo.
        total_descubiertas = len(descubrimientos)
        total_sustancias = len(SUSTANCIAS)

        lineas = [
            "🧪 TUS SUSTANCIAS DESCUBIERTAS",
            "━━━━━━━━━━━━━━━━━━",
            (
                f"📊 Progreso: "
                f"{total_descubiertas}/{total_sustancias}"
            ),
            "",
        ]

        if not descubrimientos:
            lineas.extend([
                "Todavía no has descubierto ninguna sustancia.",
                "",
                "🔬 Empieza con /constructor H2O",
            ])

            await mensaje.reply_text("\n".join(lineas))
            return

        lineas.extend(
            f"{i}. {fila['nombre']} — {fila['formula']}"
            for i, fila in enumerate(descubrimientos, start=1)
        )

        texto = "\n".join(lineas)

        # Telegram limita el tamaño de cada mensaje.
        for inicio in range(0, len(texto), 3800):
            await mensaje.reply_text(texto[inicio:inicio + 3800])

        return

    # ==================== BÚSQUEDA POR FÓRMULA ====================

    coincidencias = _buscar_por_formula(argumento)

    if coincidencias:
        nuevos = []

        for sustancia in coincidencias:
            formula = _formula_normalizada(sustancia["formula"])

            if registrar_descubrimiento(
                usuario.id,
                formula,
                sustancia["nombre"],
            ):
                nuevos.append(sustancia)

        if nuevos:
            nombres = "\n".join(
                f"• {sustancia['formula']} — {sustancia['nombre']}"
                for sustancia in nuevos
            )

            await mensaje.reply_text(
                "🎉 ¡Felicidades! Has descubierto:\n\n" + nombres
            )

        for sustancia in coincidencias:
            await mensaje.reply_text(_texto_sustancia(sustancia))

        return

    # ==================== BÚSQUEDA POR NOMBRE ====================

    por_nombre = _buscar_por_nombre(argumento)

    if por_nombre:
        descubiertas = [
            sustancia
            for sustancia in por_nombre
            if usuario_descubrio_nombre(
                usuario.id,
                sustancia["nombre"],
            )
        ]

        if not descubiertas:
            await mensaje.reply_text(
                "🔒 Todavía no has descubierto esa sustancia.\n"
                "Primero escribe su fórmula química exacta."
            )
            return

        for sustancia in descubiertas:
            await mensaje.reply_text(_texto_sustancia(sustancia))

        return

    # ==================== NO ENCONTRADA ====================

    await mensaje.reply_text(
        "❌ No encontré esa fórmula o sustancia.\n\n"
        "Las fórmulas distinguen mayúsculas y minúsculas: "
        "H2O es válida, pero h2o no.\n"
        "Los nombres no distinguen mayúsculas y minúsculas.\n\n"
        "Usa /constructor para ver las instrucciones."
    )