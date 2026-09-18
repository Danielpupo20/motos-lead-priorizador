¿Qué hace?

Ingesta — carga conversaciones de WhatsApp en texto plano desde data/raw/.
Normalización y deduplicación — limpia números de teléfono, elimina duplicados y estandariza nombres.
Extracción con IA — envía cada conversación a Gemini (gemini-3.1-flash-lite) y extrae: modelo de interés, presupuesto/cuota, forma de pago, intención de compra, objeción principal y si el cliente pidió cita.
Scoring — calcula un score de 0 a 100 por lead basado en los factores extraídos y clasifica cada lead como Alta prioridad (≥70), Prioridad media (40–69) o Baja prioridad (<40).
Carga a BD — guarda todos los resultados en SQLite (db/priorizador.db).
Dashboard — interfaz web en Streamlit que permite a cada asesor ver sus leads ordenados por score, con filtros por prioridad y búsqueda por nombre.
Arquitectura
WhatsApp exports (txt)
        │
        ▼
   src/ingesta.py          ← carga archivos de conversación
        │
        ▼
   src/normalizacion.py    ← limpieza, deduplicación
        │
        ▼
   src/extraccion_ia.py    ← Google Gemini API (LLM)
        │
        ▼
   src/scoring.py          ← cálculo de score 0-100
        │
        ▼
   src/carga_bd.py         ← SQLite (priorizador.db)
        │
        ▼
   dashboard/app.py        ← Streamlit (UI web)

Orquestación: GitHub Actions (cron diario 6am UTC + disparo manual)
Cómo ejecutar
Requisitos
Python 3.11+
API key de Google Gemini (gratuita en https://aistudio.google.com/apikey)
Instalación local
bash
git clone https://github.com/Danielpupo20/motos-lead-priorizador
cd motos-lead-priorizador
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
Configuración

Crea un archivo .env en la raíz del proyecto:

GEMINI_API_KEY=tu_api_key_aqui
Ejecutar el pipeline completo
bash
python -m src.pipeline

Esto procesa las 677 conversaciones, calcula scores y guarda en la base de datos.

Ejecutar el dashboard
bash
streamlit run dashboard/app.py
Automatización (GitHub Actions)

El pipeline corre automáticamente todos los días a las 6am UTC vía cron job. También puede dispararse manualmente desde la pestaña Actions del repositorio → "Pipeline de priorización de leads" → "Run workflow".

Para configurar la automatización en un repo nuevo:

Agrega GEMINI_API_KEY como secreto en Settings → Secrets → Actions
Activa "Read and write permissions" en Settings → Actions → General → Workflow permissions
Base de datos

Motor: SQLite (db/priorizador.db)

Tablas principales:

empresas — comercializadoras registradas
asesores — vendedores activos por empresa
leads — clientes potenciales normalizados
extracciones_ia — resultados del análisis de Gemini por conversación
scores — score y temperatura (Alta/Media/Baja) por lead
asignaciones — relación lead ↔ asesor

El script de creación del esquema está en src/carga_bd.py.

Stack tecnológico
Componente	Tecnología
Lenguaje	Python 3.11
IA generativa	Google Gemini (gemini-3.1-flash-lite)
Base de datos	SQLite
Dashboard	Streamlit
Orquestación	GitHub Actions
Despliegue	Streamlit Cloud
Decisiones tomadas
SQLite sobre PostgreSQL: el volumen de datos (677 leads, ~5 asesores por empresa) no justifica un motor cliente-servidor. SQLite es suficiente, portátil y no requiere infraestructura adicional.
Gemini free tier: permite procesar hasta 500 conversaciones por día sin costo. Para producción se escalaría a un plan de pago o se distribuiría el procesamiento en múltiples días.
Streamlit sobre React/Django: permite construir una interfaz de datos funcional y profesional en horas, sin necesidad de un backend separado ni build process.
GitHub Actions como orquestador: cero infraestructura adicional, log de ejecuciones automático, secretos manejados de forma segura, y disparo manual para demos.
Score 0-100: escala intuitiva para asesores comerciales. Alta (≥70) = llamar hoy; Media (40-69) = trabajar esta semana; Baja (<40) = seguimiento programado.
Supuestos asumidos
Las conversaciones de WhatsApp están en texto plano con formato estándar de exportación.
Un lead = un número de teléfono único. Si el mismo número aparece en múltiples conversaciones, se conserva la más reciente.
El score se recalcula cada vez que corre el pipeline (no acumula histórico de scores anteriores).
Las empresas y asesores están precargados en la base de datos; el pipeline no crea nuevos asesores automáticamente.
La cuota gratuita de Gemini (500 requests/día) es suficiente para el volumen actual procesando en días consecutivos.
Qué haría con más tiempo
Procesar las 677 conversaciones completas — actualmente se procesaron 484/677 por límite de cuota diaria de la API gratuita. Con un plan de pago o más días de ejecución se completaría el dataset.
Agregar gráficas de analítica — distribución de leads por ciudad, modelos más solicitados, comparativa de performance entre asesores y tendencia de scores en el tiempo.
Sistema de actualización de estado — que el asesor pueda marcar un lead como "contactado", "en seguimiento" o "convertido" directamente desde el dashboard, y que ese estado se persista en la BD.
Checkpoint de extracción — guardar qué conversaciones ya fueron procesadas para que el pipeline retome desde donde se quedó en lugar de empezar desde cero en cada ejecución.
Notificaciones automáticas — enviar al asesor un resumen diario por WhatsApp o email con sus leads de alta prioridad del día.
Autenticación — login por asesor para que cada uno solo vea sus propios leads sin necesidad de seleccionar su nombre manualmente.
Estructura del repositorio
motos-lead-priorizador/
├── .github/
│   └── workflows/
│       └── pipeline.yml       ← automatización GitHub Actions
├── dashboard/
│   └── app.py                 ← dashboard Streamlit
├── data/
│   ├── raw/                   ← conversaciones WhatsApp originales
│   └── processed/             ← extracciones_ia.csv (salida del pipeline)
├── db/
│   └── priorizador.db         ← base de datos SQLite
├── docs/                      ← documentación adicional
├── src/
│   ├── __init__.py
│   ├── pipeline.py            ← orquestador principal
│   ├── ingesta.py
│   ├── normalizacion.py
│   ├── extraccion_ia.py
│   ├── scoring.py
│   └── carga_bd.py
├── .env.example               ← plantilla de variables de entorno
├── .gitignore
├── requirements.txt
└── README.md

Desarrollado como prueba técnica de ingeniería de datos e IA · Septiembre 2026
