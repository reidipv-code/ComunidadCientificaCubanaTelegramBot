import os
import sqlite3
from pathlib import Path


def _db_path():
    configurada = os.getenv("DATABASE_PATH", "").strip()

    if configurada:
        ruta = Path(configurada)
    else:
        ruta = (
            Path(__file__).resolve().parent.parent
            / "quimica.sqlite3"
        )

    ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta


def _connect():
    conexion = sqlite3.connect(
        _db_path(),
        timeout=15,
    )
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA busy_timeout=15000")
    return conexion


def inicializar_db():
    with _connect() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS perfiles (
                user_id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                username TEXT,
                xp INTEGER NOT NULL DEFAULT 0,
                partidas INTEGER NOT NULL DEFAULT 0,
                victorias INTEGER NOT NULL DEFAULT 0,
                preguntas_correctas INTEGER NOT NULL DEFAULT 0,
                preguntas_respondidas INTEGER NOT NULL DEFAULT 0,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def registrar_usuario(
    user_id: int,
    nombre: str,
    username: str | None = None,
):
    inicializar_db()

    with _connect() as conexion:
        conexion.execute(
            """
            INSERT INTO perfiles (user_id, nombre, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                nombre = excluded.nombre,
                username = excluded.username,
                actualizado_en = CURRENT_TIMESTAMP
            """,
            (
                int(user_id),
                nombre or f"Jugador {user_id}",
                username,
            ),
        )

        fila = conexion.execute(
            "SELECT * FROM perfiles WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()

        return dict(fila)


def obtener_perfil(user_id: int):
    inicializar_db()

    with _connect() as conexion:
        fila = conexion.execute(
            "SELECT * FROM perfiles WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()

        return dict(fila) if fila else None


def agregar_xp(user_id: int, cantidad: int):
    cantidad = max(0, int(cantidad))
    inicializar_db()

    with _connect() as conexion:
        cursor = conexion.execute(
            """
            UPDATE perfiles
            SET xp = MIN(xp + ?, 249500),
                actualizado_en = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (cantidad, int(user_id)),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe el perfil del usuario {user_id}."
            )

        fila = conexion.execute(
            "SELECT * FROM perfiles WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()

        return dict(fila)


def registrar_resultado(
    user_id: int,
    *,
    victoria: bool,
    correctas: int,
    respondidas: int,
):
    inicializar_db()

    with _connect() as conexion:
        cursor = conexion.execute(
            """
            UPDATE perfiles SET
                partidas = partidas + 1,
                victorias = victorias + ?,
                preguntas_correctas = preguntas_correctas + ?,
                preguntas_respondidas = preguntas_respondidas + ?,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                1 if victoria else 0,
                max(0, int(correctas)),
                max(0, int(respondidas)),
                int(user_id),
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe el perfil del usuario {user_id}."
            )


def nivel_desde_xp(xp: int) -> int:
    # Cada nivel requiere 500 EXP.
    # Nivel máximo: 500.
    return min(500, max(1, int(xp) // 500 + 1))


def xp_para_siguiente_nivel(xp: int) -> int:
    if nivel_desde_xp(xp) >= 500:
        return 0

    return 500 - (int(xp) % 500)
