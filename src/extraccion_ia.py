"""
Usa Google Gemini (free tier) para extraer informacion estructurada de cada
conversacion de WhatsApp: modelo de interes, presupuesto/cuota, forma de pago,
intencion, objecion principal y si pidio cita.
 
Requiere GEMINI_API_KEY en el archivo .env.
"""
import os
import re
import json
import time
import pandas as pd
from dotenv import load_dotenv
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
 
load_dotenv()
 
MODEL_NAME = "gemini-3.1-flash-lite"
 
PROMPT_TEMPLATE = """Eres un asistente que analiza conversaciones de WhatsApp entre
un cliente y un asesor de venta de motos en Colombia.
 
A partir de la conversacion, extrae estos 6 campos. Si un dato no aparece
explicitamente, usa null (no inventes).
 
- modelo_interes: modelo de moto mencionado por el cliente (texto tal como lo dijo)
- presupuesto_cuota: monto de presupuesto o cuota inicial mencionado (texto)
- forma_pago: "contado", "credito" o null
- intencion: "alta", "media" o "baja" segun que tan cerca esta de comprar
- objecion_principal: la duda u objecion principal del cliente (texto corto) o null
- pidio_cita: true si pidio cita, visita a la sede o cotizacion formal; false si no
 
Conversacion:
{conversacion}
 
Responde SOLO con el JSON, sin texto adicional."""
 
CAMPOS_VACIOS = {
    "modelo_interes": None, "presupuesto_cuota": None, "forma_pago": None,
    "intencion": None, "objecion_principal": None, "pidio_cita": None,
}
 
 
def _formatear_conversacion(mensajes):
    return "\n".join(f"{m['emisor']}: {m['texto']}" for m in mensajes)
 
 
class CuotaDiariaAgotada(Exception):
    pass
 
 
def _extraer_una(cliente, mensajes, reintentos=4):
    texto = _formatear_conversacion(mensajes)
    prompt = PROMPT_TEMPLATE.format(conversacion=texto)
    for intento in range(reintentos):
        try:
            respuesta = cliente.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            resultado = json.loads(respuesta.text)
            if isinstance(resultado, list):
                if resultado and isinstance(resultado[0], dict):
                    resultado = resultado[0]
                else:
                    raise ValueError("Respuesta en formato de lista inesperado")
            return resultado
        except Exception as e:
            texto_error = str(e)
            if "PerDay" in texto_error:
                # cuota diaria agotada: reintentar no sirve de nada hasta mañana
                raise CuotaDiariaAgotada(texto_error) from e
            if intento == reintentos - 1:
                return {**CAMPOS_VACIOS, "error_extraccion": texto_error}
            espera = _segundos_de_espera_sugeridos(e)
            time.sleep(espera)
 
 
def _segundos_de_espera_sugeridos(error) -> float:
    """Si Google indica cuanto esperar (retryDelay), respeta ese tiempo
    exacto en vez de adivinar. Si no viene, usa un valor conservador."""
    match = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+(?:\.\d+)?)", str(error))
    if match:
        return float(match.group(1)) + 1  # +1s de margen
    return 10.0
 
 
def _mapa_lead_id_original_a_final(leads_limpios: pd.DataFrame) -> dict:
    """conversaciones.json trae el lead_id original; tras la dedup el lead_id
    final puede ser otro. Este mapa traduce original -> final."""
    mapa = {}
    for _, fila in leads_limpios.iterrows():
        for original in str(fila["lead_ids_origen"]).split("|"):
            mapa[original] = fila["lead_id"]
    return mapa
 
 
CAMPOS_CSV = ["conversacion_id", "lead_id", "modelo_interes", "presupuesto_cuota",
              "forma_pago", "intencion", "objecion_principal", "pidio_cita",
              "error_extraccion"]
 
 
def extraer_info_incremental(conversaciones: list, leads_limpios: pd.DataFrame,
                              ruta_csv, pausa_seg: float = 6.0) -> pd.DataFrame:
    """
    Version resumible: guarda cada conversacion en ruta_csv apenas se procesa
    (no espera al final) y, si se vuelve a correr, salta las que ya salieron
    bien (evita gastar cuota de la API reprocesando lo ya hecho). Pensada
    para correr tanto manualmente como desde el pipeline automatizado.
    """
    import csv
    from pathlib import Path
 
    ruta_csv = Path(ruta_csv)
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
 
    ya_ok = set()
    if ruta_csv.exists():
        previo = pd.read_csv(ruta_csv)
        ya_ok = set(previo[previo["error_extraccion"].isna()]["conversacion_id"])
 
    pendientes = [c for c in conversaciones if c["conversacion_id"] not in ya_ok]
 
    api_key = os.environ.get("GEMINI_API_KEY")
    if pendientes and not api_key:
        if ruta_csv.exists():
            print("  Falta GEMINI_API_KEY; se reutiliza data/processed/extracciones_ia.csv")
            pendientes = []
        else:
            raise RuntimeError("Falta GEMINI_API_KEY en el archivo .env")

    if pendientes and (genai is None or types is None):
        if ruta_csv.exists():
            print("  Falta google-genai; se reutiliza data/processed/extracciones_ia.csv")
            pendientes = []
        else:
            raise RuntimeError("Falta la dependencia opcional google-genai")

    if pendientes:
        cliente = genai.Client(api_key=api_key)
        mapa_ids = _mapa_lead_id_original_a_final(leads_limpios)
        nuevo_archivo = not ruta_csv.exists()
 
        with open(ruta_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
            if nuevo_archivo:
                writer.writeheader()
            for i, conv in enumerate(pendientes, 1):
                try:
                    info = _extraer_una(cliente, conv["mensajes"])
                except CuotaDiariaAgotada:
                    print(f"  Cuota diaria de {MODEL_NAME} agotada. "
                          f"Se detiene aqui ({i - 1}/{len(pendientes)} procesadas en esta corrida). "
                          f"Vuelve a correr mas tarde/mañana para completar el resto.")
                    break
                info["conversacion_id"] = conv["conversacion_id"]
                info["lead_id"] = mapa_ids.get(conv["lead_id"], conv["lead_id"])
                writer.writerow({k: info.get(k) for k in CAMPOS_CSV})
                f.flush()
                print(f"  [{i}/{len(pendientes)}] {conv['conversacion_id']} -> {info.get('intencion')}")
                if i < len(pendientes):
                    time.sleep(pausa_seg)
 
    resultado = pd.read_csv(ruta_csv)
    # una fila por lead_id final (si dos conversaciones cayeron en el mismo
    # lead fusionado, se queda con la mas reciente)
    return resultado.drop_duplicates(subset="lead_id", keep="last")
 
 
def extraer_info(conversaciones: list, leads_limpios: pd.DataFrame,
                  limite: int | None = None, pausa_seg: float = 4.0) -> pd.DataFrame:
    """
    limite: si se pasa, solo procesa las primeras N conversaciones (util para
            probar sin agotar la cuota gratuita antes de correr las 677).
    pausa_seg: espera entre llamadas para respetar el limite de requests/min
               del free tier de Gemini.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY en el archivo .env")
    if genai is None or types is None:
        raise RuntimeError("Falta la dependencia opcional google-genai")
    cliente = genai.Client(api_key=api_key)
 
    mapa_ids = _mapa_lead_id_original_a_final(leads_limpios)
 
    filas = []
    lote = conversaciones[:limite] if limite else conversaciones
    for i, conv in enumerate(lote, 1):
        info = _extraer_una(cliente, conv["mensajes"])
        info["conversacion_id"] = conv["conversacion_id"]
        info["lead_id"] = mapa_ids.get(conv["lead_id"], conv["lead_id"])
        filas.append(info)
        print(f"  [{i}/{len(lote)}] {conv['conversacion_id']} -> {info.get('intencion')}")
        if i < len(lote):
            time.sleep(pausa_seg)
 
    return pd.DataFrame(filas)