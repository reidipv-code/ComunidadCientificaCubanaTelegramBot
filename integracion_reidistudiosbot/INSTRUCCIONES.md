# Activar la EXP compartida con ReidiStudiosBot

El bot de Química es independiente, pero ReidiStudiosBot guarda los niveles y la EXP en su propia SQLite. Dos servicios de Railway no pueden compartir automáticamente ese archivo SQLite. Por eso el bot de Química usa una API autenticada que se ejecuta dentro del servicio de ReidiStudiosBot y modifica la misma base de datos.

## 1. Añade el archivo de la API

Copia `xp_api.py` de esta carpeta al repositorio de ReidiStudiosBot en la ruta:

`core/xp_api.py`

## 2. Conecta la API en el bot principal

En el `bot_railway.py` de ReidiStudiosBot, añade este import junto a los demás:

```python
from core.xp_api import iniciar_api_xp
```

Dentro de `main()`, después de `init_db()` y antes de `app.run_polling()`, añade:

```python
iniciar_api_xp()
```

No reemplaces el resto del archivo. El bot de Química no necesita estar en el mismo repositorio.

## 3. Variables de entorno de Railway

En el servicio de ReidiStudiosBot, añade:

- `XP_API_TOKEN`: una clave secreta larga y aleatoria.
- Asegúrate de que el servicio tenga un dominio público de Railway habilitado.

En el servicio del bot de Química, configura:

- `BOT_TOKEN`: token del bot de Química.
- `XP_API_URL`: dominio público de ReidiStudiosBot, sin `/xp` al final. Ejemplo: `https://tu-dominio.up.railway.app`
- `XP_API_TOKEN`: exactamente el mismo secreto que configuraste en ReidiStudiosBot.

No publiques ni compartas `XP_API_TOKEN`.

## 4. Prueba

Abre `https://TU-DOMINIO/health`. Debe responder con `{"ok":true,"service":"reidistudios-xp-api"}`.

Después de desplegar el bot de Química, prueba `/trivia 9` con una cuenta ya registrada en ReidiStudiosBot. Al completar la partida, la EXP se suma a la cuenta existente y el nivel se calcula con la función progresiva que ya usa `core/db.py`.

**Importante:** no he hecho cambios en GitHub ni en Railway. Esta integración debe añadirse y desplegarse explícitamente en ReidiStudiosBot para que la EXP sea realmente compartida.
