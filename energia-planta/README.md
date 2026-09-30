# energia-planta

Laboratorio Streamlit (CRISP-DM) que entrena y compara tres modelos sobre `Usage_kWh` (kWh cada 15 min):
Elastic Net (línea base), Random Forest y XGBoost. El gemelo digital de MineTwin solo consume el artefacto
exportado `artefactos/planta_xgboost.json`.

## Puesta en marcha

```bash
pip install -r requirements.txt
# Coloque Steel_industry_data.csv (UCI / Kaggle Steel Industry) en data/  (no se versiona)
streamlit run app.py     # abre el laboratorio, una fase CRISP-DM por pantalla
python train.py          # entrenamiento completo sin interfaz (ver más abajo)
```

## Estructura

| Ruta | Contenido |
| --- | --- |
| `app.py` | Menú lateral con las 8 fases CRISP-DM |
| `screens/` | Una pantalla por fase (`negocio`, `datos`, `eda`, `pruebas`, `preparacion`, `modelado`, `evaluacion`, `despliegue`) |
| `lab/` | Módulos importables: datos, contrato de variables, pruebas, modelos, evaluación, explicabilidad, exportación |
| `artefactos/` | Resultados en caché. Los JSON pequeños se versionan; `*.joblib`, `*.csv` y `*.parquet` no |
| `data/` | CSV original (ignorado por git) |

## Decisiones de diseño

- **Objetivo:** `Usage_kWh`, métrica principal MAE en kWh.
- **Señales del modelo:** solo las que el gemelo produce: hora del día (seno/coseno sobre la hora fraccionaria,
  periodo 24), día de la semana (one-hot) y tipo de carga (Light / Medium / Maximum, derivado del tonelaje SAG
  frente al nominal: menor a 75 % ligera, hasta 90 % media, mayor a 90 % máxima). Reactiva, factor de potencia,
  NSM y WeekStatus no entran; el CO2 se calcula después desde los kWh.
- **Convención de tiempo:** el archivo marca el final de cada intervalo de 15 min y el registro de medianoche
  (NSM = 0) lleva la fecha del día que cierra. Se reconstruye `ts_end` y se usa `ts_start = ts_end - 15 min`.
- **Validación:** entrenamiento del 1 de enero al 30 de septiembre de 2018; dentro de él, `TimeSeriesSplit` para
  buscar hiperparámetros (`RandomizedSearchCV`, semilla 42, MAE); se congelan; el último trimestre (1 oct - 31 dic)
  es el examen y no se toca durante el ajuste.
- **Costo:** el trabajo pesado no corre en cada recarga de Streamlit. Las pantallas leen `artefactos/` y ofrecen
  un botón "Entrenar / Re-entrenar" que llama al mismo código que `train.py`.
