"""
Pipeline end-to-end: ingesta -> normalizacion -> extraccion IA -> scoring -> carga a BD.
Un solo disparo, sin pasos manuales. Se ejecuta con: python -m src.pipeline
"""
from pathlib import Path
from src import ingesta, normalizacion, extraccion_ia, scoring, carga_bd


def run():
    print("1/5 Ingesta...")
    crudos = ingesta.cargar_fuentes()

    print("2/5 Normalizacion y deduplicacion...")
    leads_limpios = normalizacion.normalizar_y_deduplicar(crudos)

    print("3/5 Extraccion con IA sobre conversaciones...")
    ruta_extracciones = Path(__file__).resolve().parent.parent / "data" / "processed" / "extracciones_ia.csv"
    extracciones = extraccion_ia.extraer_info_incremental(
        crudos["conversaciones"], leads_limpios, ruta_extracciones
    )

    print("4/5 Scoring...")
    scores = scoring.calcular_scores(leads_limpios, extracciones, crudos["historico_cierres"])

    print("5/5 Carga a base de datos...")
    carga_bd.persistir(leads_limpios, extracciones, scores, crudos)

    print("Pipeline completo.")


if __name__ == "__main__":
    run()
