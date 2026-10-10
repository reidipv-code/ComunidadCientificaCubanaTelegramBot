import os
import httpx


class XPAPIError(Exception):
    pass


def _configuracion():
    base = os.getenv("XP_API_URL", "").strip().rstrip("/")
    token = os.getenv("XP_API_TOKEN", "").strip()
    if not base or not token:
        raise XPAPIError(
            "Faltan XP_API_URL o XP_API_TOKEN. Configura la integración con ReidiStudiosBot."
        )
    return base, token


async def consultar_usuario(user_id: int):
    base, token = _configuracion()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{base}/xp/user",
                params={"user_id": user_id},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise XPAPIError(f"No se pudo consultar ReidiStudiosBot: {exc}") from exc

    if not data.get("registered"):
        return False
    return True


async def otorgar_xp(user_id: int, cantidad: int, request_id: str):
    base, token = _configuracion()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{base}/xp/add",
                json={
                    "user_id": int(user_id),
                    "amount": int(cantidad),
                    "request_id": request_id,
                    "source": "trivia_quimica",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise XPAPIError(f"No se pudo registrar la EXP en ReidiStudiosBot: {exc}") from exc

    if not data.get("ok"):
        raise XPAPIError(data.get("error", "La API no confirmó la EXP."))
    return data
