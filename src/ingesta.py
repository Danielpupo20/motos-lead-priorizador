"""
Carga los 5 archivos fuente desde data/raw sin intervencion manual.
"""
import json
import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def cargar_fuentes() -> dict:
    """Devuelve un dict con cada fuente cargada en memoria (DataFrames + JSON crudo)."""
    leads = pd.read_csv(RAW_DIR / "leads.csv")
    catalogo = pd.read_csv(RAW_DIR / "catalogo_motos.csv")
    asesores = pd.read_csv(RAW_DIR / "asesores.csv")
    historico_cierres = pd.read_csv(RAW_DIR / "historico_cierres.csv")
    with open(RAW_DIR / "conversaciones.json", encoding="utf-8") as f:
        conversaciones = json.load(f)

    return {
        "leads": leads,
        "catalogo": catalogo,
        "asesores": asesores,
        "historico_cierres": historico_cierres,
        "conversaciones": conversaciones,
    }
