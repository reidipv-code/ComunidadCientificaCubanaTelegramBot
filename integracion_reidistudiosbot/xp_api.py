"""
Copiar este archivo a ReidiStudiosBot/core/xp_api.py.
El API usa la misma base SQLite y la función de progresión de XP de core.db.
"""
import hmac
import os
import sqlite3
import threading

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from core.db import DB_PATH, esta_registrado, obtener_datos, xp_para_nivel


def _autorizado(request: Request) -> bool:
    secreto = os.getenv("XP_API_TOKEN", "").strip()
    if not secreto:
        return False
    recibido = request.headers.get("Authorization", "")
    esperado = f"Bearer {secreto}"
    return hmac.compare_digest(recibido, esperado)


async def health(request: Request):
    return JSONResponse({"ok": True, "service": "reidistudios-xp-api"})


async def consultar_usuario(request: Request):
    if not _autorizado(request):
        return JSONResponse({"ok": False, "error": "No autorizado"}, status_code=401)

    try:
        user_id = int(request.query_params.get("user_id", ""))
    except ValueError:
        return JSONResponse({"ok": False, "error": "user_id inválido"}, status_code=400)

    if not esta_registrado(user_id):
        return JSONResponse({"ok": True, "registered": False})

    datos = obtener_datos(user_id)
    if not datos:
        return JSONResponse({"ok": True, "registered": False})

    return JSONResponse({
        "ok": True,
        "registered": True,
        "nombre": datos[0],
        "xp": int(datos[3] or 0),
        "nivel": int(datos[4] or 1),
    })


async def agregar_xp(request: Request):
    if not _autorizado(request):
        return JSONResponse({"ok": False, "error": "No autorizado"}, status_code=401)

    try:
        payload = await request.json()
        user_id = int(payload.get("user_id"))
        cantidad = int(payload.get("amount"))
        request_id = str(payload.get("request_id", "")).strip()
    except (ValueError, TypeError, AttributeError):
        return JSONResponse({"ok": False, "error": "Datos inválidos"}, status_code=400)

    if cantidad not in (25, 50, 100):
        return JSONResponse({"ok": False, "error": "Cantidad de EXP no permitida"}, status_code=400)
    if not request_id or len(request_id) > 120:
        return JSONResponse({"ok": False, "error": "request_id inválido"}, status_code=400)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS xp_api_requests (
                request_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        anterior = conn.execute(
            "SELECT user_id, amount FROM xp_api_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()

        if anterior:
            if int(anterior["user_id"]) != user_id or int(anterior["amount"]) != cantidad:
                return JSONResponse(
                    {"ok": False, "error": "request_id reutilizado con datos diferentes"},
                    status_code=409,
                )
            fila = conn.execute(
                "SELECT xp, nivel FROM usuarios WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return JSONResponse({
                "ok": True,
                "duplicate": True,
                "nivel": int(fila["nivel"]) if fila else 1,
                "leveled_up": False,
            })

        fila = conn.execute(
            "SELECT xp, nivel FROM usuarios WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not fila:
            return JSONResponse(
                {"ok": False, "error": "Usuario no registrado en ReidiStudiosBot"},
                status_code=404,
            )

        xp = max(0, int(fila["xp"] or 0)) + cantidad
        nivel_original = max(1, min(int(fila["nivel"] or 1), 500))
        nivel = nivel_original

        if nivel >= 500:
            xp = min(xp, xp_para_nivel(500))
        else:
            while nivel < 500:
                requisito = xp_para_nivel(nivel)
                if xp < requisito:
                    break
                xp -= requisito
                nivel += 1

            if nivel >= 500:
                nivel = 500
                xp = min(xp, xp_para_nivel(500))

        conn.execute(
            "UPDATE usuarios SET xp = ?, nivel = ? WHERE user_id = ?",
            (xp, nivel, user_id),
        )
        conn.execute(
            "INSERT INTO xp_api_requests (request_id, user_id, amount) VALUES (?, ?, ?)",
            (request_id, user_id, cantidad),
        )
        conn.commit()

        return JSONResponse({
            "ok": True,
            "duplicate": False,
            "nivel": nivel,
            "leveled_up": nivel > nivel_original,
        })
    except sqlite3.Error:
        conn.rollback()
        return JSONResponse(
            {"ok": False, "error": "Error accediendo a la base de datos"},
            status_code=500,
        )
    finally:
        conn.close()


app = Starlette(routes=[
    Route("/health", health, methods=["GET"]),
    Route("/xp/user", consultar_usuario, methods=["GET"]),
    Route("/xp/add", agregar_xp, methods=["POST"]),
])


def iniciar_api_xp():
    if not os.getenv("XP_API_TOKEN", "").strip():
        print("⚠️ XP API no iniciada: falta XP_API_TOKEN.")
        return

    port = int(os.getenv("PORT") or os.getenv("XP_API_PORT") or "8080")
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    hilo = threading.Thread(
        target=server.run,
        name="reidistudios-xp-api",
        daemon=True,
    )
    hilo.start()
    print(f"✅ API privada de EXP iniciada en el puerto {port}.")
