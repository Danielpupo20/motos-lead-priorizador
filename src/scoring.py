"""
Calcula un score de prioridad explicable por lead, combinando senales de
leads + extracciones_ia, y lo valida contra historico_cierres.csv.

TODO (siguiente sesion): definir pesos de cada senal y la funcion de
validacion (tasa de cierre real por bucket Frio/Tibio/Caliente).
"""
import pandas as pd


def calcular_scores(leads_limpios: pd.DataFrame, extracciones: pd.DataFrame,
                     historico_cierres: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("Pendiente: logica de scoring")
