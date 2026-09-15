"""
Usa la API de Claude para extraer info estructurada de cada conversacion:
modelo de interes, presupuesto/cuota inicial, forma de pago, intencion,
objecion principal, si pidio cita.

TODO (siguiente sesion): definir el prompt con salida JSON estricta,
llamar la API por conversacion (o en lote), y parsear/validar la respuesta.
"""
import pandas as pd


def extraer_info(conversaciones: list, leads_limpios: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("Pendiente: integracion con Claude API")
