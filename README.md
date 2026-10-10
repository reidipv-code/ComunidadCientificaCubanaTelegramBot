# Trivia de Química para Telegram

Bot independiente de Telegram para partidas de preguntas de Química con EXP compartida con ReidiStudiosBot.

## Archivos principales

- `Procfile`: comando de inicio para Railway.
- `bot_railway.py`: inicia el bot y registra `/start`, `/trivia` y los botones.
- `requirements.txt`: dependencias.
- `comandos/trivia.py`: interpreta los grados.
- `juegos/trivia.py`: partidas, vidas, botones, tiempo y recompensas.
- `juegos/preguntas.py`: filtra preguntas por grado.
- `data/preguntas.json`: banco completo.
- `integracion_reidistudiosbot/`: API que se debe añadir al bot principal para compartir EXP de verdad.

## Comandos

Se aceptan combinaciones arbitrarias de grados:

- `/trivia 8`
- `/trivia 9`
- `/trivia 8 y 9`
- `/trivia 8 y 10 y 12`
- `/trivia 8 y 9 y 10 y 11 y 12`

También acepta separadores como comas o espacios, por ejemplo `/trivia 8, 10, 12`.

## Mecánica

- 10 preguntas aleatorias por partida.
- Cuatro botones por pregunta: tres respuestas incorrectas y una correcta.
- 3 vidas.
- 10 segundos por pregunta.
- Perder las tres vidas termina la partida, da 0 EXP y activa un enfriamiento de 90 segundos.
- Completar las 10 preguntas da 100 EXP con 3 vidas, 50 EXP con 2 vidas o 25 EXP con 1 vida.
- Las recompensas se registran en el sistema de XP de ReidiStudiosBot; no se guarda un XP independiente en este bot.

## Banco de preguntas

`data/preguntas.json` contiene 640 preguntas: las 615 entradas que se pudieron extraer del archivo `Texto pegado.txt` (14 preguntas fijas, cinco bloques de 118 preguntas y 11 preguntas de familias) más 25 preguntas adicionales redactadas para el juego. Las preguntas del archivo están repartidas entre grados por dificultad práctica; una misma pregunta puede estar disponible para más de un grado. Las opciones se mezclan al iniciar cada pregunta.

El archivo fuente anunciaba aproximadamente 733 preguntas, pero los bloques presentes en el texto suman 615. No he inventado las 118 entradas que faltan de ese total anunciado.

En las preguntas de estado físico, el archivo fuente solo tenía tres opciones; se añadió `Plasma` como cuarta opción incorrecta para cumplir la mecánica de cuatro botones.

## Variables de entorno del bot de Química

```env
BOT_TOKEN=TOKEN_DEL_BOT_DE_QUIMICA
XP_API_URL=https://DOMINIO-PUBLICO-DE-REIDISTUDIOSBOT
XP_API_TOKEN=EL_MISMO_SECRETO_EN_AMBOS_SERVICIOS
LOG_LEVEL=INFO
```

Para la configuración de la API de EXP, sigue `integracion_reidistudiosbot/INSTRUCCIONES.md`.

## Railway

Usa el `Procfile` incluido. Añade las variables de entorno anteriores en el servicio de Química y despliega el código en el servicio nuevo. No se ha subido nada a GitHub ni desplegado nada en Railway.
