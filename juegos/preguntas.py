import json
from pathlib import Path


RUTA_BANCO = Path(__file__).resolve().parent.parent / "data" / "preguntas.json"


def _cargar_banco():
    with RUTA_BANCO.open("r", encoding="utf-8") as archivo:
        preguntas = json.load(archivo)

    validas = []
    for pregunta in preguntas:
        opciones = pregunta.get("options", [])
        if len(opciones) != 4:
            continue
        if sum(1 for opcion in opciones if opcion.get("correct")) != 1:
            continue
        pregunta["grades"] = [int(g) for g in pregunta.get("grades", [])]
        validas.append(pregunta)
    return validas


BANCO_PREGUNTAS = _cargar_banco()


def obtener_preguntas(grados):
    seleccionados = set(int(g) for g in grados)
    resultado = [
        pregunta for pregunta in BANCO_PREGUNTAS
        if seleccionados.intersection(pregunta["grades"])
    ]
    return resultado
