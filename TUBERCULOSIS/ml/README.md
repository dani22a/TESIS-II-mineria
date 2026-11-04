# ML pipeline (SP-02)

Reproducible experimental pipeline for TB screening from chest X-rays. It is a research scaffold:
the numbers it prints on synthetic data are plumbing checks, **not scientific results**.

```bash
cd ml
pip install -r requirements.txt          # CPU torch is enough: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install mlflow                       # optional (logging is skipped gracefully if missing)

python -m pytest -q                      # unit tests: splits/leakage, metrics, bootstrap, DeLong, McNemar, Holm, model shapes, Grad-CAM
python -m tbml.smoke                     # end to end on SYNTHETIC data, CPU, minutes
```

## Real-data run

```bash
python -m tbml.data_prep --layout shenzhen --raw /data/raw --out data/processed/tb --size 224
python -m tbml.train --manifest data/processed/tb/manifest.csv --out runs/exp1 \
    --trials 30 --epochs 15 --img-size 224 --external-institutions montgomery --mlflow
python -m tbml.evaluate --run runs/exp1 --n-boot 2000 [--cv-metrics cv_metrics.csv]
python -m tbml.explain  --run runs/exp1 --manifest data/processed/tb/manifest.csv --n 10
```

## Modules (`tbml/`)

| Module | Content |
|---|---|
| `data_prep.py` | hash dedupe, QC, normalization, `LungSegmenter` hook (placeholder default) |
| `synthetic.py` | synthetic tiny dataset (smoke test only) |
| `splits.py` | `GroupShuffleSplit` / `GroupKFold` on patient (or institution), `assert_no_leakage`, external-institution hold-out |
| `models.py` | DenseNet121, EfficientNet-B3 (torchvision), compact ViT, CNN-Transformer hybrid, EfficientNet-BiLSTM-Attention |
| `train.py` | Optuna TPE + MedianPruner (`--trials`), best-val-AUC checkpoint, Platt calibration and threshold (Youden or `--target-sensitivity`) fitted on the validation split only |
| `evaluate.py` | sensitivity, specificity, F1, MCC, AUC-ROC, AUC-PR, Brier/ECE, false-negative analysis, patient-grouped bootstrap CI, McNemar (exact), DeLong, Holm; Friedman/Wilcoxon only with matched blocks |
| `explain.py` | Grad-CAM (CNN models, incl. hybrid stem and EfficientNet-BiLSTM), attention rollout (ViT) |
| `tracking.py` | optional MLflow wrapper |

## Methodological rules built in

- Splits are grouped by patient; `assert_no_leakage` also checks identical image hashes. An external
  institution is removed before splitting and never used for tuning, calibration or threshold.
- Optuna selects on validation AUC; threshold and calibration use validation only; test/external are read once by `evaluate`.
- Bootstrap resamples patients, not images. McNemar/DeLong here treat images as independent (collapse to one image per patient when patients have several).
- Friedman/Wilcoxon need >=3 models and >=5 identical blocks (e.g. the same grouped CV folds for all models); otherwise `evaluate` reports `applicable: false`. Test images are not blocks. Producing `cv_metrics.csv` (a grouped CV loop around `train.run_model`) is not automated yet.
- Models train from scratch by default (`weights=None`, no downloads). `pretrained=True` (ImageNet) is supported by the torchvision-based models via `model_kw` but not exposed on the CLI.
- Synthetic runs are stamped `SYNTHETIC — not scientific results` in reports, calibration files and heatmaps.

## Limitations

Segmentation is a placeholder; no real data was used here; MIMIC-CXR/VinDr need credentialed access
(see `data/README.md`); no performance claim is made. See `docs/requisitos.md` for the product-level limits.
