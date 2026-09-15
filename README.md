# Priorizador de Leads con IA — Motos y Motores del Norte

## Que hace
Pendiente de completar a medida que se construye el pipeline.

## Como se ejecuta
```
pip install -r requirements.txt
cp .env.example .env   # completar ANTHROPIC_API_KEY
python -m src.pipeline
streamlit run dashboard/app.py
```

## Decisiones tomadas
- SQLite versionado en el repo (esquema en db/schema.sql): cumple el requisito de motor
  relacional sin depender de infraestructura externa.
- Claude API para la extraccion estructurada de conversaciones.
- GitHub Actions (cron + workflow_dispatch) para la automatizacion punta a punta.
- Streamlit Community Cloud para la publicacion.

## Supuestos
(Pendiente)

## Que haria con mas tiempo
(Pendiente)
