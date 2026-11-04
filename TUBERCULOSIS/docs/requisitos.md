# SP-02 - Requisitos, decisiones y recursos faltantes

Tamizaje asistido de tuberculosis pulmonar con radiografias de torax (ficha TEMATICA-SP-02). Alcance actual: MVP.

## Requisitos de la ficha

- Modelos a comparar: DenseNet121, EfficientNetB3, ViT, CNN-Transformer, EfficientNet-BiLSTM-Attention.
- Datasets: Shenzhen TB, MIMIC-CXR (acceso credenciado, no anonimo), VinDr-CXR.
- Salida: "tuberculosis probable" / "sin hallazgos compatibles", mas estado separado "no evaluable".
- Particion por paciente/institucion, validacion externa, Grad-CAM y calibracion.
- Web con 4 roles (administrador, operador, revisor, auditor), auditoria append-only, tablero y reportes.

## Decisiones

- FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL local (`DATABASE_URL`).
- Almacenamiento en disco detras de una interfaz `Storage` (reemplazable por MinIO).
- Motor de inferencia DEMO determinista, marcado `is_demo=true`, `model_version=demo-0`.
- Auditoria inmutable por trigger en BD; eventos de modulo idempotentes por `client_event_id`.
- El LLM nunca ve imagenes ni identificadores; el flujo central funciona sin LLM.

## Recursos faltantes

| Recurso | Nota |
|---|---|
| Shenzhen TB | Descargar y verificar licencia. |
| MIMIC-CXR | Acceso credenciado en PhysioNet (CITI + DUA); no redistribuir. |
| VinDr-CXR | Solicitar acceso en PhysioNet. |
| Pesos preentrenados | Definir fuente (ImageNet/timm) y licencias. |
| GPU | No disponible localmente; evaluar Colab/servidor. |
| Clave de LLM | Opcional. |
| Conexiones n8n | Workflows WF-01..06 escritos pero NO probados en una instancia n8n real; faltan credenciales (SMTP, header auth) y probar la importacion. |
| Docker/podman | No instalado localmente: los compose no se ejecutaron; verificacion local con PostgreSQL 18 / SQLite. |
