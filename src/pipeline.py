name: Pipeline de priorizacion de leads
 
on:
  schedule:
    - cron: "0 6 * * *"   # todos los dias 6am UTC
  workflow_dispatch: {}     # permite dispararlo manualmente para la demo
 
permissions:
  contents: write   # necesario para que el workflow pueda commitear los resultados
 
jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python -m src.pipeline
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      - name: Guardar base de datos y progreso de extraccion actualizados
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add db/priorizador.db data/processed/extracciones_ia.csv
          git diff --staged --quiet || git commit -m "chore: actualizar datos del pipeline [automatico]"
          git push