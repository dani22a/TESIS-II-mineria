# Guía: Copiloto Langflow en MineTwin AI

Esta guía explica en lenguaje simple **qué se implementó**, **cómo levantarlo** y **cómo probarlo**.

Se tomó como referencia el proyecto `langflow-language-tutor` (tutor de idiomas con Langflow + Postgres + componentes en Python) y se adaptó a los casos de uso de MineTwin.

---

## 1. Qué se hizo

Se agregó un **segundo motor** al módulo **Copiloto IA**. Arriba a la derecha hay un selector:

| Motor | Dónde corre | Para qué sirve |
|---|---|---|
| **LangGraph** (el que ya existía) | En el navegador | Supervisor con aprobación humana (sin cambios) |
| **Langflow** (nuevo) | En Docker/Podman (`http://127.0.0.1:7861`) | Flujo **visual** y editable, con base de datos de procedimientos y bitácora de turno |

### Equivalencia con el tutor de idiomas

| Tutor de idiomas | MineTwin Langflow |
|---|---|
| Tabla `words` (vocabulario) | Tablas `procedimientos` (SOP de la mina) y `bitacora_turno` |
| Upload Word File (CSV) | **Upload Procedure File** (CSV de procedimientos) |
| Word Loader → Prompt | **Procedure Loader** y **Logbook Loader** → Prompts |
| Add word tool | **Registrar en bitácora** |
| Create Story Tool (agente como herramienta) | **Informe de Turno** (agente como herramienta) |
| Language Agent | **Copiloto MineTwin** |
| — | Herramientas conectadas al gemelo: consultar estado, Kuz-Ram, escenario what-if, explicar DRL, proponer acción |

### La idea clave: Langflow no inventa ni recalcula

Las herramientas de Langflow **no copian la física a Python**. Llaman por HTTP al servidor de MineTwin (`npm run dev`), que ejecuta **los mismos motores** de la app (Kuz-Ram, Scenario Lab, DRL) sobre el estado del gemelo que está viendo el operador.

```
Navegador (Copiloto IA, motor Langflow)
   │  pregunta + estado del gemelo
   ▼
Vite dev server  /api/langflow/run ──────────►  Langflow (flujo "MineTwin Copilot")
   ▲                                               │ el agente elige herramienta
   │  /api/twin/tools/*  ◄─────────────────────────┤ estado, Kuz-Ram, what-if, DRL, proponer
   │  (mismos motores TS)                          │
   │                                               └─► Postgres: procedimientos y bitácora
   ▼
Respuesta + línea de tiempo de herramientas + propuesta para aprobar (HITL)
```

**Aprobación humana (HITL):** la herramienta `proponer_accion` **no ejecuta nada**. Crea una propuesta que aparece en el chat con **Aprobar / Rechazar** y en la cola HITL del encabezado. Al decidir, la app aplica (o no) el cambio en el gemelo y le avisa a Langflow para que **registre la decisión en la bitácora**.

---

## 2. Requisitos

- Podman (o Docker Desktop) instalado.
- Node.js y las dependencias de `minetwin-ai` (`npm install`).
- Python 3 (solo para el script que crea el flujo).
- `GEMINI_API_KEY` en `minetwin-ai/.env` (la misma que usa el copiloto LangGraph). El `docker-compose` la lee de ahí; no hay que copiarla en otro lado.

> La imagen de Langflow pesa ~2,5 GB. Si ya levantaste el tutor de idiomas, ya está descargada.

---

## 3. Cómo levantarlo (paso a paso)

Todo desde PowerShell, en la carpeta `minetwin-ai`.

**Paso 1: la app**

```powershell
npm run dev
```

Déjala corriendo. Langflow la necesita para consultar el gemelo.

**Paso 2: Langflow + Postgres** (otra terminal)

```powershell
.\langflow\start.ps1
```

Este script inicia Podman, detecta las IPs de tu PC y levanta los contenedores. Espera alrededor de 1 minuto y abre `http://127.0.0.1:7861`.

**Paso 3: crear el flujo** (solo la primera vez, o si cambias los componentes)

```powershell
python .\langflow\scripts\setup_flow.py
```

Salida esperada:

```
variable GOOGLE_API_KEY creada
flujo creado ...
endpoint: http://127.0.0.1:7861/api/v1/run/minetwin-copilot
```

**Paso 4: probar**

Abre `http://localhost:3000` → **Copiloto IA** → selector **Langflow**. Debe aparecer el badge verde **Langflow conectado** y el botón **Abrir editor**.

**Para apagar:**

```powershell
cd langflow; podman compose down
```

---

## 4. Pruebas y qué deberías ver

Escribe estas preguntas en el chat (o usa los botones de ejemplo) con el motor **Langflow** activo.

| # | Pregunta | Herramienta esperada (línea de tiempo) | Resultado esperado |
|---|---|---|---|
| A | ¿Cuántos camiones están esperando en cada pala ahora? | `query_twin_state` | Colas reales por pala (ej. EX-01: 2, EX-02: 1) |
| B | Si subo el factor de carga 8%, ¿qué pasa con P80 y kWh/t del SAG? | `run_kuz_ram` | P80 y kWh/t actual vs propuesto (ej. 375 → 353 mm) |
| C | Si se rompe la pala EX-01 y además llueve, ¿cuánto baja la producción? | `run_what_if_scenario` | Producción y cuellos de botella. **El gemelo no cambia.** |
| D | Explícame la recomendación REC-DRL-001 como auditoría. | `explain_drl_recommendation` | Qué, por qué, KPIs vivos, recompensa |
| E | Hay cola en una pala: propón mover camiones a la otra. | `propose_action` | Recuadro amarillo con **Aprobar / Rechazar** |
| F | (Apruebas la propuesta de E) | `registrar_evento_bitacora` | "Acción aprobada…" + confirmación del registro en bitácora |
| G | ¿Qué dice el procedimiento cuando una pala tiene mucha cola? | ninguna | Cita el código **SOP-DSP-01** |
| H | Registra en la bitácora que empezó a llover en la rampa principal. | `registrar_evento_bitacora` | Evento guardado (categoría CLIMA) |
| I | Genera el informe de turno. | `query_twin_state` | Informe con KPIs reales, eventos de la bitácora y SOP citados |

**Cómo comprobar que no inventa cifras:** compara los números de la respuesta con el JSON en **Línea de tiempo de herramientas** (derecha) y con las pantallas Load & Haul / Mine-to-Mill.

**Cómo ver la bitácora en la base de datos:**

```powershell
podman exec minetwin-langflow-postgres-1 psql -U langflow -d langflow -c "select * from bitacora_turno order by id"
```

### Probar directo en Langflow (sin la app)

1. Abre `http://127.0.0.1:7861` → flujo **MineTwin Copilot**.
2. Pulsa **Playground**.
3. Las preguntas G y H funcionan solas. Las que usan el gemelo (A–F, I) responden "No hay un gemelo activo" hasta que envíes al menos una pregunta desde la app. Así debe ser: el gemelo vive en el navegador.

### Cargar más procedimientos (como el CSV del tutor)

1. En el nodo **Upload Procedure File**, sube `langflow/data/procedimientos_extra.csv` (columnas `codigo,dominio,titulo,regla`).
2. Ejecuta el nodo (flecha ▶). Debe decir `Correcto: 4 procedimientos cargados`.
3. Pregunta: *¿Qué procedimiento aplica al mineral skarn?* → debe citar **SOP-PLT-03**.

---

## 5. Si algo falla

| Lo que ves | Qué hacer |
|---|---|
| Badge **Langflow no disponible** | ¿Corriste `.\langflow\start.ps1`? Espera 1 minuto. Revisa `podman compose ps` dentro de `langflow/`. |
| `Gemini rechazó la llamada por cuota o tope de gasto (429)` | Tu proyecto de Google AI Studio llegó al límite. Súbelo en https://ai.studio/spend o cambia `GEMINI_API_KEY` en `.env` y vuelve a correr `setup_flow.py`. |
| `No se pudo conectar con MineTwin` en una respuesta | `npm run dev` no está corriendo, o cambiaste de red. Vuelve a correr `.\langflow\start.ps1`: recalcula las IPs. |
| `No hay un gemelo activo` | Envía la consulta desde la app (no desde el Playground). |
| Flujo no encontrado (404) | Corre `python .\langflow\scripts\setup_flow.py`. |
| Cambiaste un `.py` de `custom_components` y no se nota | Langflow guarda el código dentro del flujo: `podman restart minetwin-langflow-langflow-1` y luego `setup_flow.py`. |
| Bitácora vacía tras reinstalar | El seed de Postgres solo corre al crear el volumen: `podman compose down -v` y levanta de nuevo. |

---

## 6. Detalles técnicos que vale la pena saber (para la tesis)

- **Podman sobre WSL:** dentro del contenedor, `host.containers.internal` apunta a la VM de WSL, **no** a Windows. Por eso `start.ps1` pasa las IPs reales de Windows en `MINETWIN_API_URL` (lista separada por comas; los componentes prueban en orden). Con Docker Desktop, `host.docker.internal` funciona sin más.
- **Vite 6 bloquea hosts desconocidos:** se agregó `server.allowedHosts` en `vite.config.ts` para aceptar las llamadas del contenedor.
- **`stream=False` en los agentes:** con Gemini y streaming activo, el Agent de Langflow solo conservaba el primer fragmento cuando el modelo escribía → llamaba una herramienta → seguía escribiendo. Resultado: respuestas cortadas y, peor, el agente principal **completaba el informe inventando cifras**. Con `stream=False` se corrigió.
- **Nombre de la herramienta del informe:** un Agent en modo herramienta se expone con un nombre genérico (`Call_Agent_message_response`). `setup_flow.py` le pide a Langflow el campo `tools_metadata` y lo renombra a `generar_informe_turno` con una descripción clara; sin esto, el agente principal nunca lo usaba.
- **Informe sin duplicar:** Langflow concatena el texto del sub-agente con el del agente principal; por eso el prompt pide que, tras el informe, el copiloto responda con una sola línea.
- **La clave de Gemini** vive como variable global `GOOGLE_API_KEY` dentro de Langflow; el JSON exportado del flujo no la contiene.

### Variables opcionales (en `minetwin-ai/.env`)

| Variable | Por defecto | Para qué |
|---|---|---|
| `LANGFLOW_URL` | `http://127.0.0.1:7861` | Dónde está Langflow |
| `LANGFLOW_FLOW_ID` | `minetwin-copilot` | Endpoint o ID del flujo |
| `LANGFLOW_API_KEY` | vacío | Solo si desactivas el auto-login de Langflow |

---

## 7. Mapa de archivos

| Archivo | Para qué |
|---|---|
| `langflow/docker-compose.yml` | Langflow (puerto 7861) + Postgres (puerto 5435) |
| `langflow/start.ps1` | Levanta todo y detecta las IPs de Windows |
| `langflow/postgres/init.sql` | Tablas y datos iniciales de procedimientos y bitácora |
| `langflow/data/procedimientos_extra.csv` | CSV de ejemplo para el nodo Upload |
| `langflow/custom_components/minetwin/*.py` | Los 9 componentes custom (herramientas, loaders, upload) |
| `langflow/scripts/setup_flow.py` | Crea o actualiza el flujo por API y lo exporta |
| `langflow/flows/minetwin-copilot.json` | Flujo exportado (respaldo; importable a mano) |
| `src/services/langflow/bridgeServer.ts` | Puente: `/api/langflow/*` y `/api/twin/tools/*` |
| `src/services/langflow/langflowClient.ts` | Cliente del navegador |
| `src/components/views/CopilotView.tsx` | Selector LangGraph/Langflow, prompts y HITL |
| `vite.config.ts` | Registra el puente y `allowedHosts` |
