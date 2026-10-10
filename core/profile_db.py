
import os
import sqlite3
from pathlib import Path


def _db_path():
    configured = os.getenv("DATABASE_PATH", "").strip()

    if configured:
        path = Path(configured)
    else:
        path = Path(__file__).resolve().parent.parent / "quimica.sqlite3"

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect():
    conn = sqlite3.connect(_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def inicializar_db():
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

    with _connect() as conn:
        conn.execute("""
            INSERT INTO perfiles (user_id, nombre, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                nombre = excluded.nombre,
                username = excluded.username,
                actualizado_en = CURRENT_TIMESTAMP
        """, (
            int(user_id),
            nombre or "Jugador",
            username,
        ))

        fila = conn.execute(
            "SELECT * FROM perfiles WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()

        return dict(fila)


def obtener_perfil(user_id: int):
    inicializar_db()

    with _connect() as conn:
        fila = conn.execute(
            "SELECT * FROM perfiles WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()

        return dict(fila) if fila else None


def listar_usuarios():
    """Devuelve usuarios ordenados del registro más antiguo al más reciente."""
    inicializar_db()

    with _connect() as conn:
        filas = conn.execute("""
            SELECT user_id, nombre, username, creado_en, xp
            FROM perfiles
            ORDER BY datetime(creado_en) ASC, user_id ASC
        """).fetchall()

        return [dict(fila) for fila in filas]


def agregar_xp(user_id: int, cantidad: int):
    inicializar_db()
    cantidad = max(0, int(cantidad))

    with _connect() as conn:
        cursor = conn.execute("""
            UPDATE perfiles
            SET xp = xp + ?,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (cantidad, int(user_id)))

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe el perfil del usuario {user_id}."
            )

        fila = conn.execute(
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

    with _connect() as conn:
        cursor = conn.execute("""
            UPDATE perfiles SET
                partidas = partidas + 1,
                victorias = victorias + ?,
                preguntas_correctas = preguntas_correctas + ?,
                preguntas_respondidas = preguntas_respondidas + ?,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (
            1 if victoria else 0,
            max(0, int(correctas)),
            max(0, int(respondidas)),
            int(user_id),
        ))

        if cursor.rowcount == 0:
            raise ValueError(
                f"No existe el perfil del usuario {user_id}."
            )


def nivel_desde_xp(xp: int) -> int:
    # Cada nivel requiere 500 EXP; el máximo es el nivel 500.
    return min(500, max(1, int(xp) // 500 + 1))


def xp_para_siguiente_nivel(xp: int) -> int:
    if nivel_desde_xp(xp) >= 500:
        return 0

    return 500 - (int(xp) % 500)
