"""
Normaliza telefono/fecha/ciudad/canal/nombre y deduplica leads cross-canal.
 
Decisiones (documentadas para el README):
- Llave de dedup: telefono normalizado (10 digitos) > email > nombre+ciudad normalizados.
  El telefono es la unica llave confiable: hay leads con el mismo telefono pero
  nombres muy distintos entre si (ej: "Julian Perez Arias" vs "J. Perez Arias").
- Fechas ambiguas dd/mm vs mm/dd: se asume formato colombiano (dia primero) salvo
  que el primer numero sea > 12, en cuyo caso solo puede ser dd/mm.
- Al fusionar duplicados: se conserva la fecha_registro mas antigua (primer contacto
  real) y se listan todos los canales por los que escribio esa persona.
"""
import re
import unicodedata
import pandas as pd
from dateutil import parser as dateparser
 
CANAL_MAP = {
    "whatsapp": "WhatsApp",
    "meta ads": "Meta Ads",
    "formulario web": "Formulario Web",
}
 
CIUDAD_MAP = {
    "bogota": "Bogotá", "bogota dc": "Bogotá", "bogota d.c.": "Bogotá",
    "monteria": "Montería",
    "itagui": "Itagüí",
    "sta marta": "Santa Marta", "santa marta": "Santa Marta",
    "medellin": "Medellín",
    "soledad": "Soledad",
    "cartagena": "Cartagena", "cartagena de indias": "Cartagena",
    "soacha": "Soacha",
    "rio negro": "Rionegro", "rionegro": "Rionegro",
    "bello": "Bello",
    "b/quilla": "Barranquilla", "barranquilla": "Barranquilla",
}
 
 
def _sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
 
 
def normalizar_telefono(tel):
    if pd.isna(tel):
        return None
    digitos = re.sub(r"\D", "", str(tel))
    if len(digitos) >= 10:
        return digitos[-10:]
    return None
 
 
def normalizar_canal(canal):
    if pd.isna(canal):
        return None
    return CANAL_MAP.get(str(canal).strip().lower())
 
 
def normalizar_ciudad(ciudad):
    if pd.isna(ciudad):
        return None
    clave = _sin_tildes(str(ciudad).strip().lower())
    return CIUDAD_MAP.get(clave, str(ciudad).strip().title())
 
 
def normalizar_nombre(nombre):
    if pd.isna(nombre):
        return None
    limpio = re.sub(r"\s+", " ", str(nombre).strip())
    return limpio.title()
 
 
def normalizar_fecha(fecha):
    if pd.isna(fecha):
        return None
    texto = str(fecha).strip()
    primer_numero = re.match(r"(\d{1,2})[-/]", texto)
    dayfirst = True
    if primer_numero and int(primer_numero.group(1)) > 12:
        dayfirst = True  # solo puede ser dia
    try:
        return dateparser.parse(texto, dayfirst=dayfirst).isoformat()
    except (ValueError, OverflowError):
        return None
 
 
def _llave_dedup(row):
    if row["telefono_normalizado"]:
        return f"tel:{row['telefono_normalizado']}"
    if pd.notna(row.get("email")) and str(row["email"]).strip():
        return f"mail:{str(row['email']).strip().lower()}"
    return f"nom:{row['nombre_normalizado']}|{row['ciudad_normalizada']}"
 
 
def normalizar_y_deduplicar(crudos: dict) -> pd.DataFrame:
    df = crudos["leads"].copy()
 
    df["telefono_normalizado"] = df["telefono"].apply(normalizar_telefono)
    df["canal_normalizado"] = df["canal"].apply(normalizar_canal)
    df["ciudad_normalizada"] = df["ciudad"].apply(normalizar_ciudad)
    df["nombre_normalizado"] = df["nombre_cliente"].apply(normalizar_nombre)
    df["fecha_registro_norm"] = df["fecha_registro"].apply(normalizar_fecha)
    df["llave_dedup"] = df.apply(_llave_dedup, axis=1)
 
    df = df.sort_values("fecha_registro_norm")
 
    filas = []
    for llave, grupo in df.groupby("llave_dedup"):
        base = grupo.iloc[0].copy()  # registro mas antiguo
        base["lead_ids_origen"] = "|".join(grupo["lead_id"])
        base["canales"] = "|".join(sorted(grupo["canal_normalizado"].dropna().unique()))
        for campo in ["email", "ciudad_normalizada", "nombre_normalizado"]:
            if pd.isna(base[campo]) or not str(base[campo]).strip():
                completos = grupo[campo].dropna()
                if len(completos):
                    base[campo] = completos.iloc[0]
        filas.append(base)
 
    resultado = pd.DataFrame(filas).reset_index(drop=True)
    return resultado
