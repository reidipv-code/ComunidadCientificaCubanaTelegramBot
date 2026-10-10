# core/constructor_db.py

from core.profile_db import _connect


def inicializar_constructor_db():
    """Crea la tabla de sustancias descubiertas si no existe."""

    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS descubrimientos_sustancias (
                user_id INTEGER NOT NULL,
                formula TEXT NOT NULL,
                nombre TEXT NOT NULL,
                descubierto_en TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (
                    user_id,
                    formula,
                    nombre
                )
            )
        """)


def registrar_descubrimiento(
    user_id: int,
    formula: str,
    nombre: str
) -> bool:
    """
    Registra un descubrimiento.

    Devuelve True si es nuevo y False si ya existía.
    """

    inicializar_constructor_db()

    with _connect() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO descubrimientos_sustancias (
                user_id,
                formula,
                nombre
            )
            VALUES (?, ?, ?)
        """, (
            int(user_id),
            formula,
            nombre,
        ))

        return cursor.rowcount > 0


def usuario_descubrio_nombre(
    user_id: int,
    nombre: str
) -> bool:
    """Comprueba si el usuario ya descubrió una sustancia."""

    inicializar_constructor_db()

    with _connect() as conn:
        fila = conn.execute("""
            SELECT 1
            FROM descubrimientos_sustancias
            WHERE
                user_id = ?
                AND nombre = ? COLLATE NOCASE
            LIMIT 1
        """, (
            int(user_id),
            nombre,
        )).fetchone()

        return fila is not None


def listar_descubrimientos(user_id: int):
    """Devuelve las sustancias descubiertas por un usuario."""

    inicializar_constructor_db()

    with _connect() as conn:
        filas = conn.execute("""
            SELECT
                nombre,
                formula,
                MIN(descubierto_en) AS descubierto_en
            FROM descubrimientos_sustancias
            WHERE user_id = ?
            GROUP BY
                nombre,
                formula
            ORDER BY
                nombre COLLATE NOCASE ASC
        """, (
            int(user_id),
        )).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]