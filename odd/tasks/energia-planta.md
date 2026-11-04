# energia-planta

**Objective:** Streamlit CRISP-DM lab (`energia-planta/`) trains/compares Elastic Net, Random Forest, XGBoost on `Usage_kWh`; the MineTwin twin consumes the exported JSON and shows plant kWh/15 min.
**Constraints:** Kuz-Ram SAG kWh/t untouched. Model uses only hour, weekday, load type. CO2 excluded. Seed 42. CSV (Kaggle/UCI Steel Industry) in `energia-planta/data/`, not committed. Train Jan-Sep, TimeSeriesSplit tuning, last quarter = untouched exam.
**TDD:** suggestion-based (tests only after user approval). **Checks:** app import/run smoke, `npm run lint` (tsc), artifact schema readback.
**Delivery:** ask-on-risk; forecast > 400 lines -> single feature branch, user decides push/PR.

## Tasks
- [x] T1 Folder, CSV, requirements, Streamlit shell (CRISP-DM menu), Business + Data-quality screens. Route: delegated writer.
- [x] T2 EDA + Tests screens (reading under each figure). Route: delegated writer.
- [x] T3 Preparation, 3 models, temporal validation, random search, frozen hyperparams.
- [x] T4 SHAP, Friedman/Nemenyi + Diebold-Mariano, evaluation, deployment, export `artefactos/planta_xgboost.json`.
- [x] T5 Twin: types, `plantEnergy.ts`, Mine-Mill card, copilot citation, graceful fallback.
- [x] T6 Streamlit UX refinement (accepted scope change requested by the user). Route: single delegated writer.

## Progress / evidence
(commits and checks recorded per task)
- T1 a6a5647 feat(energia-planta): shell + Negocio + Datos. Evidence: AppTest renders screens 1-2 without exception (1 and 1 plotly charts, 1 and 3 tables). Data facts: 35,040 rows, 0 missing 15-min slots, 0 duplicates, 365 midnight records stamped with the closing day (rebuilt ts_end = day + NSM, +1 day if NSM==0; features/split use ts_start = ts_end - 15 min), all values in range. Range 2018-01-01 00:15 .. 2019-01-01 00:00 (ts_start 2018-01-01 00:00 .. 2018-12-31 23:45); train 26,208 rows / exam 8,832 rows; the 2019-01-01 00:00 record starts 2018-12-31 23:45 so it falls in the exam.
- T2 8e2beb5 feat(energia-planta): EDA + Pruebas screens. Evidence: AppTest renders EDA (6 plotly figures) and Pruebas (1 figure, 5 tables) without exception; each figure/table has the 3-line reading built from computed numbers. Key results: KW by load H=17,109 (eps2 0.49), Dunn all pairs p<0.001; MW weekday vs weekend p<0.001; Spearman CO2 0.88, VIF CO2 43.1 (kWh 50.4); KPSS level 2.34 (p<=0.01), ACF lag1 0.91.
- T3 1d379b9 feat(energia-planta): pipelines, TimeSeriesSplit(5) + RandomizedSearchCV (seed 42, MAE), frozen hyperparameters. Evidence: run_modeling() completed in ~65 s; frozen CV MAE: Elastic Net 18.84, Random Forest 12.44, XGBoost 12.48 kWh; Preparación and Modelado render without exception; Modelado degrades to a 'not trained' message when artefactos/hiperparametros_congelados.json is missing.
- T4 4c7593c feat(energia-planta): evaluation, SHAP, export. Evidence: `python train.py` completed (115 s, exit 0). Exam MAE/RMSE/MAPE/R2: Elastic Net 17.202/23.631/230.8%/0.453; Random Forest 11.577/19.506/100.0%/0.627; XGBoost 11.490/19.295/100.2%/0.635. Friedman (13 weekly windows) chi2 20.46 p 3.6e-5, ranks EN 3.00 RF 1.69 XGB 1.31. DM Dec XGB vs EN p 4.5e-9; vs RF p 0.0092 (p 0.045 with 1-day HAC lag). Winner XGBoost. planta_xgboost.json validated by export.validate_artifact: 12 top-level keys, 504 rows, 24 scenarios, finite numbers. All 8 screens render via AppTest without exception.
- T5 9614600 feat(minetwin): plantEnergy service + mill fields + artifact copy; a05bed1 feat(minetwin): Mine-Mill plant energy card; 12a1192 feat(minetwin): plant copilot cites plant kWh. Route: delegated writer. Evidence: `npm run lint` (tsc --noEmit) clean before and after; `npm run build` OK; tsx script: SAG 2500/3400/3700/4200 t/h at Mon 06:00 -> Light 3.23 / Medium 46.88 / Maximum 61.62 / Maximum 61.62 kWh (at Mon 14:00: 3.92 / 80.35 / 71.40 / 71.40, model itself has Maximum < Medium at that hour); missing JSON -> status 'unavailable', predict null, no throw; tick leaves mill.plant* undefined when unloaded and sets them once loaded, specificEnergyKwhPerTon untouched. Not verified visually in a browser. Constants: SAG_NOMINAL_TPH=4000, clock Monday 06:00 start, time scale 60.
- T6 e0aff2a feat(energia-planta): shared page layout, theme, glossary; screens/lab presentation changes landed in 18c9e0a (an automatic commit titled 'add skill registry...' swept them in); 3fe20ba README Interfaz + KPI fix. Evidence: AppTest, all 8 screens render without exception with artifacts (metrics/tabs per screen OK) and with artefactos/data pointed at an empty temp dir (friendly banner on screens 1-7 and 8, 0 exceptions); next-step button navigates (1 -> 2). Visual: one screenshot of Negocio + sidebar seen (loopback 127.0.0.1:8599), KPI truncation fixed; other pages NOT visually verified. Server stopped, port 8599 not listening. No push.

## Next step
user decides push & PR
