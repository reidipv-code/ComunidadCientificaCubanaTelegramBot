# core/profile_db.py

import os
import shutil
import sqlite3
import logging

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


logger = logging.getLogger(__name__)

ZONA_HORARIA = ZoneInfo("America/Havana")

# Ubicación anterior de la base de datos.
RUTA_ANTIGUA = (
    Path(__file__).resolve().parent.parent
    / "quimica.sqlite3"
)

# Ubicación persistente de Railway.
RUTA_PERSISTENTE = Path("/data/quimica.sqlite3")


def hora_cuba():
    """Devuelve la fecha y hora actual de Cuba."""
    return datetime.now(ZONA_HORARIA).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _db_path():
    """
    Obtiene la ruta de SQLite.

    Prioridad:
    1. DATABASE_PATH, si está configurada.
    2. /data/quimica.sqlite3 en Railway.
    3. La ubicación anterior si /data no está disponible.
    """

    configured = os.getenv(
        "DATABASE_PATH",
        ""
    ).strip()

    if configured:
        path = Path(configured)
    elif Path("/data").is_dir():
        path = RUTA_PERSISTENTE
    else:
        path = RUTA_ANTIGUA

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Intentar conservar la base de datos anterior.
    # Nunca reemplazar una base de datos de destino existente.
    if (
        path.resolve() != RUTA_ANTIGUA.resolve()
        and not path.exists()
        and RUTA_ANTIGUA.is_file()
    ):
        try:
            shutil.copy2(
                RUTA_ANTIGUA,
                path
            )

            logger.info(
                "Base de datos anterior copiada a %s",
                path
            )

        except OSError:
            logger.exception(
                "No se pudo copiar la base de datos anterior."
            )
            raise

    logger.info(
        "Ruta de la base de datos SQLite: %s",
        path
    )

    return path


def _connect():
    """Abre una conexión SQLite con configuración segura."""
    conn = sqlite3.connect(
        _db_path(),
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA busy_timeout=30000"
    )

    return conn


def inicializar_db():
    """Crea la tabla de perfiles si todavía no existe."""

    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perfiles (
                user_id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                username TEXT,
                xp INTEGER NOT NULL DEFAULT 0,
                partidas INTEGER NOT NULL DEFAULT 0,
                victorias INTEGER NOT NULL DEFAULT 0,
                preguntas_correctas INTEGER NOT NULL DEFAULT 0,
                preguntas_respondidas INTEGER NOT NULL DEFAULT 0,
                creado_en TEXT NOT NULL,
                actualizado_en TEXT NOT NULL
            )
        """)

    logger.info(
        "Tabla de perfiles inicializada correctamente."
    )


def registrar_usuario(
    user_id: int,
    nombre: str,
    username: str | None = None,
):
    """
    Registra un usuario nuevo.

    Si ya existe, actualiza su nombre y username
    sin reiniciar su EXP ni sus estadísticas.
    """

    inicializar_db()

    ahora = hora_cuba()

    with _connect() as conn:
        conn.execute("""
            INSERT INTO perfiles (
                user_id,
                nombre,
                username,
                creado_en,
                actualizado_en
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                nombre = excluded.nombre,
                username = excluded.username,
                actualizado_en = excluded.actualizado_en
        """, (
            int(user_id),
            nombre or "Jugador",
            username,
            ahora,
            ahora,
        ))

        fila = conn.execute(
            """
            SELECT *
            FROM perfiles
            WHERE user_id = ?
            """,
            (int(user_id),)
        ).fetchone()

        return dict(fila)


def obtener_perfil(user_id: int):
    """Obtiene el perfil de un usuario."""

    inicializar_db()

    with _connect() as conn:
        fila = conn.execute(
            """
            SELECT *
            FROM perfiles
            WHERE user_id = ?
            """,
            (int(user_id),)
        ).fetchone()

        return dict(fila) if fila else None


def listar_usuarios():
    """
    Devuelve los usuarios ordenados por fecha
    de registro, del más antiguo al más reciente.
    """

    inicializar_db()

    with _connect() as conn:
        filas = conn.execute("""
            SELECT
                user_id,
                nombre,
                username,
                creado_en,
                xp
            FROM perfiles
            ORDER BY
                datetime(creado_en) ASC,
                user_id ASC
        """).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]


def agregar_xp(
    user_id: int,
    cantidad: int
):
    """Añade EXP sin modificar las estadísticas de partidas."""

    inicializar_db()

    cantidad = max(
        0,
        int(cantidad)
    )

    with _connect() as conn:
        cursor = conn.execute("""
            UPDATE perfiles
            SET
                xp = xp + ?,
                actualizado_en = ?
            WHERE user_id = ?
        """, (
            cantidad,
            hora_cuba(),
            int(user_id),
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe el perfil del usuario {user_id}."
            )

        fila = conn.execute(
            """
            SELECT *
            FROM perfiles
            WHERE user_id = ?
            """,
            (int(user_id),)
        ).fetchone()

        return dict(fila)


def registrar_resultado(
    user_id: int,
    *,
    victoria: bool,
    correctas: int,
    respondidas: int,
):
    """Actualiza las estadísticas de una partida."""

    inicializar_db()

    with _connect() as conn:
        cursor = conn.execute("""
            UPDATE perfiles
            SET
                partidas = partidas + 1,
                victorias = victorias + ?,
                preguntas_correctas = preguntas_correctas + ?,
                preguntas_respondidas = preguntas_respondidas + ?,
                actualizado_en = ?
            WHERE user_id = ?
        """, (
            1 if victoria else 0,
            max(0, int(correctas)),
            max(0, int(respondidas)),
            hora_cuba(),
            int(user_id),
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe el perfil del usuario {user_id}."
            )


def nivel_desde_xp(xp: int) -> int:
    """Cada nivel requiere 500 EXP. Máximo: nivel 500."""

    return min(
        500,
        max(1, int(xp) // 500 + 1)
    )


def xp_para_siguiente_nivel(xp: int) -> int:
    """Calcula la EXP que falta para el próximo nivel."""

    if nivel_desde_xp(xp) >= 500:
        return 0

    return 500 - (
        int(xp) % 500
    )