"""
Calcula un score de prioridad (0-100) explicable por lead, combinando:
 
  - Urgencia (60% del score): que tan reciente es el lead. Validado contra
    historico_cierres.csv -> la tasa de cierre cae de forma monotona segun
    las horas transcurridas hasta el primer contacto (15.1% en 0-6h vs 5.8%
    en 48h+). Esto confirma en datos lo que dijo el gerente comercial: la
    demora es lo que mas mata el cierre.
  - Señales intrinsecas (40% del score): pidio_cita, presupuesto/cuota
    mencionado, forma de pago definida, intencion (extraida por IA) y
    ausencia de objecion fuerte. Estas señales muestran un efecto mas
    modesto y ruidoso en el historico (9.5% a 12.6% de cierre segun cuantas
    señales positivas tiene el lead) pero son directionalmente consistentes
    y son la unica forma de diferenciar leads con la misma antiguedad.
 
Nota: los datos son sinteticos y no estan anclados a la fecha real de
ejecucion (el fecha_registro va de enero a diciembre de 2026). Se usa la
fecha_registro mas reciente del propio dataset como referencia de "ahora" -
en produccion, con leads llegando en tiempo real, esa referencia seria
simplemente la hora actual.
"""
import pandas as pd
 
PESO_URGENCIA = 0.6
PESO_INTRINSECO = 0.4
 
 
def calcular_urgencia(horas_desde_registro) -> float:
    """100 = lead recien llegado, decae linealmente, 0 a partir de 48h."""
    if pd.isna(horas_desde_registro):
        return 0.0
    return max(0.0, 100.0 - (horas_desde_registro / 48.0) * 100.0)
 
 
def calcular_bono_intrinseco(fila_extraccion) -> float:
    puntos = 0
    if fila_extraccion.get("pidio_cita") is True:
        puntos += 20
    if pd.notna(fila_extraccion.get("presupuesto_cuota")):
        puntos += 20
    if fila_extraccion.get("forma_pago") in ("contado", "credito"):
        puntos += 15
    intencion = fila_extraccion.get("intencion")
    if intencion == "alta":
        puntos += 25
    elif intencion == "media":
        puntos += 12
    if pd.isna(fila_extraccion.get("objecion_principal")):
        puntos += 20
    return float(puntos)  # max 100
 
 
def _temperatura(score: float) -> str:
    if score >= 70:
        return "Caliente"
    if score >= 40:
        return "Tibio"
    return "Frío"
 
 
def calcular_scores(leads_limpios: pd.DataFrame, extracciones: pd.DataFrame,
                     historico_cierres: pd.DataFrame) -> pd.DataFrame:
    df = leads_limpios.merge(extracciones, on="lead_id", how="left")
 
    fechas = pd.to_datetime(df["fecha_registro_norm"], errors="coerce")
    referencia = fechas.max()
    df["horas_desde_registro"] = (referencia - fechas).dt.total_seconds() / 3600
 
    df["urgencia"] = df["horas_desde_registro"].apply(calcular_urgencia)
    df["bono_intrinseco"] = df.apply(
        lambda f: calcular_bono_intrinseco(f.to_dict()), axis=1
    )
    df["score"] = (df["urgencia"] * PESO_URGENCIA
                   + df["bono_intrinseco"] * PESO_INTRINSECO).round(1)
    df["temperatura"] = df["score"].apply(_temperatura)
 
    df["detalle_calculo"] = df.apply(
        lambda f: (
            f'{{"urgencia": {f["urgencia"]:.1f}, '
            f'"bono_intrinseco": {f["bono_intrinseco"]:.1f}, '
            f'"horas_desde_registro": {f["horas_desde_registro"]:.1f}}}'
        ), axis=1
    )
 
    return df[["lead_id", "score", "temperatura", "detalle_calculo"]]