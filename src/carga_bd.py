
"""
Persiste leads, extracciones, scores y catalogos de referencia en SQLite
(esquema en db/schema.sql). Tambien genera una asignacion simple de leads
a asesores para alimentar la vista "mis leads de hoy" del dashboard.
 
Logica de asignacion (simple e intencionalmente explicable):
- Se excluyen leads en estado "Descartado" (ya se decidio no perseguirlos).
- Dentro de cada punto de venta, los leads se ordenan por score descendente
  y se reparten en ronda entre los asesores activos de ese punto de venta,
  respetando la capacidad_diaria_leads de cada uno.
"""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
 
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "priorizador.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
 
 
def _crear_esquema(conn):
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
 
 
def _asignar_leads(leads_scores: pd.DataFrame, asesores: pd.DataFrame) -> pd.DataFrame:
    activos = asesores[asesores["activo"].str.upper() == "SI"]
    candidatos = leads_scores[leads_scores["estado_gestion_norm"] != "Descartado"]
 
    filas = []
    ahora = datetime.now(timezone.utc).isoformat()
 
    for punto_venta_id, grupo_leads in candidatos.groupby("punto_venta_id"):
        equipo = activos[activos["punto_venta_id"] == punto_venta_id]
        if equipo.empty:
            continue  # sin asesores activos en ese punto de venta
 
        grupo_leads = grupo_leads.sort_values("score", ascending=False)
        contador = {row["asesor_id"]: 0 for _, row in equipo.iterrows()}
        capacidad = dict(zip(equipo["asesor_id"], equipo["capacidad_diaria_leads"]))
        ciclo_asesores = list(contador.keys())
        i = 0
        intentos_sin_espacio = 0
 
        for _, lead in grupo_leads.iterrows():
            if intentos_sin_espacio >= len(ciclo_asesores):
                break  # todos los asesores llegaron a su capacidad
            asesor_id = ciclo_asesores[i % len(ciclo_asesores)]
            i += 1
            if contador[asesor_id] >= capacidad[asesor_id]:
                intentos_sin_espacio += 1
                continue
            contador[asesor_id] += 1
            intentos_sin_espacio = 0
            filas.append({
                "lead_id": lead["lead_id"],
                "asesor_id": asesor_id,
                "fecha_asignacion": ahora,
            })
 
    return pd.DataFrame(filas)
 
 
def persistir(leads_limpios: pd.DataFrame, extracciones: pd.DataFrame,
              scores: pd.DataFrame, crudos: dict):
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()  # reconstruir desde cero en cada corrida del pipeline
    conn = sqlite3.connect(DB_PATH)
    _crear_esquema(conn)
 
    asesores = crudos["asesores"]
    catalogo = crudos["catalogo"]
 
    empresas = pd.DataFrame({"empresa_id": leads_limpios["empresa_id"].unique()})
    empresas["nombre"] = empresas["empresa_id"]
    empresas.to_sql("empresas", conn, if_exists="append", index=False)
 
    puntos_venta = pd.concat([
        leads_limpios[["punto_venta_id", "empresa_id"]],
        asesores[["punto_venta_id", "empresa_id"]],
    ]).dropna().drop_duplicates()
    puntos_venta.to_sql("puntos_venta", conn, if_exists="append", index=False)
 
    asesores.to_sql("asesores", conn, if_exists="append", index=False)
 
    catalogo_renombrado = catalogo.rename(columns={
        "unidades_disponibles": "unidades_disponibles",
    })
    catalogo_renombrado.to_sql("catalogo_motos", conn, if_exists="append", index=False)
 
    columnas_leads = ["lead_id", "lead_ids_origen", "empresa_id", "punto_venta_id",
                       "nombre_normalizado", "telefono_normalizado", "email",
                       "ciudad_normalizada", "modelo_interes_texto", "canal_normalizado",
                       "canales", "fecha_registro_norm", "estado_gestion_norm",
                       "fecha_primer_contacto", "campania"]
    leads_bd = leads_limpios[columnas_leads].rename(columns={
        "nombre_normalizado": "nombre_cliente",
        "telefono_normalizado": "telefono_normalizado",
        "ciudad_normalizada": "ciudad",
        "canal_normalizado": "canal_origen",
        "fecha_registro_norm": "fecha_registro",
        "estado_gestion_norm": "estado_gestion",
    })
    leads_bd.to_sql("leads", conn, if_exists="append", index=False)
 
    if len(extracciones):
        cols = ["lead_id", "modelo_interes", "presupuesto_cuota", "forma_pago",
                "intencion", "objecion_principal", "pidio_cita"]
        extracciones_bd = extracciones[[c for c in cols if c in extracciones.columns]].rename(
            columns={"modelo_interes": "modelo_interes_ia"}
        )
        extracciones_bd = extracciones_bd.drop_duplicates(subset="lead_id")
        extracciones_bd.to_sql("extracciones_ia", conn, if_exists="append", index=False)
 
    scores_bd = scores.drop_duplicates(subset="lead_id")
    scores_bd.to_sql("scores", conn, if_exists="append", index=False)
 
    leads_con_score = leads_limpios.merge(scores, on="lead_id")
    asignaciones = _asignar_leads(leads_con_score, asesores)
    if len(asignaciones):
        asignaciones.to_sql("asignaciones", conn, if_exists="append", index=False)
 
    conn.commit()
    conn.close()
    print(f"Base de datos creada en {DB_PATH}")
    print(f"  leads: {len(leads_bd)} | scores: {len(scores_bd)} | asignaciones: {len(asignaciones)}")