"""
Corre (o retoma) la extraccion de IA sobre TODAS las conversaciones.
Salta las que ya estan guardadas correctamente en data/processed/extracciones_ia.csv
y solo procesa las que faltan -- se puede interrumpir y volver a correr sin
perder progreso ni gastar cuota reprocesando lo ya hecho.
 
Uso: python correr_extraccion.py
"""
from dotenv import load_dotenv
from src import ingesta, normalizacion, extraccion_ia
 
load_dotenv()
 
 
def main():
    crudos = ingesta.cargar_fuentes()
    leads_limpios = normalizacion.normalizar_y_deduplicar(crudos)
    resultado = extraccion_ia.extraer_info_incremental(
        crudos["conversaciones"], leads_limpios,
        ruta_csv="data/processed/extracciones_ia.csv",
    )
    print(f"Listo. {len(resultado)} leads con extraccion en data/processed/extracciones_ia.csv")
 
 
if __name__ == "__main__":
    main()