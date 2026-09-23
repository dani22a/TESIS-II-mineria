"""Crea o actualiza el flujo "MineTwin Copilot" en un Langflow en ejecución.

Uso (con el stack de langflow/docker-compose.yml levantado):
    python langflow/scripts/setup_flow.py

Qué hace:
1. Inicia sesión con el auto-login local de Langflow.
2. Crea/actualiza la variable global GOOGLE_API_KEY a partir de GEMINI_API_KEY (minetwin-ai/.env).
3. Lee el catálogo de componentes (/api/v1/all) y clona los nodos de esa misma versión de Langflow.
4. Crea el flujo o, si ya existe, reemplaza sus nodos y conexiones (endpoint: minetwin-copilot).
5. Exporta el flujo a langflow/flows/minetwin-copilot.json sin claves.
"""

import copy
import gzip
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.getenv("LANGFLOW_URL", "http://127.0.0.1:7861").rstrip("/")
LANGFLOW_DIR = Path(__file__).resolve().parents[1]
APP_DIR = LANGFLOW_DIR.parent
FLOW_NAME = "MineTwin Copilot"
ENDPOINT_NAME = "minetwin-copilot"
GEMINI_MODEL = "gemini-2.5-flash"

MAIN_AGENT_TEMPLATE = """Eres el copiloto operacional de MineTwin AI, un gemelo digital minero (perforación, tronadura, carguío, transporte, chancado y molienda).

Reglas estrictas:
- NUNCA inventes cifras (t/h, P80, kWh/t, colas, costos). Toda cifra debe venir de una herramienta.
- Si una herramienta devuelve un error o un resultado incompleto, dilo tal cual. Nunca completes datos faltantes por tu cuenta.
- Estado actual de la mina (colas, palas, tolva, SAG) -> usa consultar_estado_gemelo.
- Tronadura, P80, fragmentación o factor de carga -> usa calcular_kuz_ram.
- Preguntas hipotéticas ("qué pasa si", pala caída, lluvia, barro, rampa cerrada, más camiones) -> usa simular_escenario. Esto NO modifica la mina.
- Por qué la IA recomienda algo o una recomendación REC-... -> usa explicar_recomendacion.
- Si el usuario pide PROPONER, reasignar, aplicar o ejecutar una acción -> usa proponer_accion con kind = dispatch, blast o crusher. La acción queda pendiente de aprobación humana en MineTwin: dilo explícitamente y nunca afirmes que ya se ejecutó.
- Si piden anotar o registrar algo, o llega un mensaje [HITL] con una decisión del operador -> usa registrar_evento_bitacora (categoría DECISION_HITL para decisiones).
- Si piden un informe, reporte o resumen del turno -> usa generar_informe_turno. Langflow ya muestra el informe completo al usuario, así que después NO lo repitas: responde solo con la línea "Informe generado con datos del gemelo y la bitácora."
- Si preguntan qué dice un procedimiento, responde con los procedimientos vigentes de abajo, completos y citando su código (por ejemplo SOP-DSP-01).

Procedimientos operativos vigentes:
{procedimientos}

Responde en español neutro, breve, con viñetas, indicando de qué herramienta sale cada número (Kuz-Ram, laboratorio de escenarios, gemelo, DRL). No pegues JSON crudo.
"""

REPORT_TEMPLATE = """Eres el redactor del informe de turno de una mina a cielo abierto (MineTwin AI).

Primero llama a la herramienta consultar_estado_gemelo para obtener los KPIs vivos y recién después escribe el informe completo.
Usa solo las cifras de esa herramienta y solo los eventos de la bitácora de abajo. No inventes cifras ni eventos.

Bitácora reciente del turno:
{bitacora}

Procedimientos operativos:
{procedimientos}

Formato del informe (español neutro, máximo 250 palabras):
1) Título con la fecha del turno
2) KPIs: producción t/h, colas por pala, tolva del chancador y SAG (t/h y kWh/t)
3) Eventos relevantes de la bitácora
4) Riesgos o desviaciones respecto a los procedimientos (cita el código SOP)
5) Recomendación breve para el siguiente turno
"""


def load_env_value(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value.strip()
    env_path = APP_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def login() -> str:
    with urllib.request.urlopen(BASE + "/api/v1/auto_login", timeout=30) as response:
        return json.loads(response.read())["access_token"]


def request(method: str, path: str, token: str, payload=None, timeout: int = 120):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return None
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code} {detail[:1500]}") from exc


def find_component(catalog: dict, category: str, *names: str) -> dict:
    group = catalog.get(category) or {}
    for name in names:
        if name in group:
            return group[name]
    for group in catalog.values():
        if not isinstance(group, dict):
            continue
        for name in names:
            if name in group:
                return group[name]
    raise SystemExit(f"No se encontró el componente {names} en el catálogo de Langflow")


TOOL_OUTPUT = {
    "allows_loop": False,
    "cache": True,
    "display_name": "Toolset",
    "group_outputs": False,
    "hidden": None,
    "loop_types": None,
    "method": "to_toolkit",
    "name": "component_as_tool",
    "options": None,
    "required_inputs": None,
    "selected": "Tool",
    "tool_mode": True,
    "types": ["Tool"],
    "value": "__UNDEFINED__",
}


def clone_node(catalog_node, node_id, data_type, display_name, position, tool_mode=False, field_values=None, description=None):
    node = copy.deepcopy(catalog_node)
    node["display_name"] = display_name
    if description:
        node["description"] = description
    node["tool_mode"] = tool_mode
    if tool_mode:
        node["outputs"] = [copy.deepcopy(TOOL_OUTPUT)]
    for name, value in (field_values or {}).items():
        if name in node.get("template", {}) and isinstance(node["template"][name], dict):
            node["template"][name]["value"] = value
    return {
        "id": node_id,
        "type": "genericNode",
        "position": position,
        "data": {"id": node_id, "node": node, "type": data_type, "showNode": True, "display_name": display_name},
        "selected": False,
        "measured": {"width": 320, "height": 280},
        "dragging": False,
    }


def prompt_variable_field(name: str) -> dict:
    return {
        "type": "str",
        "required": False,
        "placeholder": "",
        "list": False,
        "show": True,
        "multiline": True,
        "value": "",
        "name": name,
        "display_name": name,
        "advanced": False,
        "dynamic": False,
        "info": "",
        "title_case": False,
        "input_types": ["Message", "Text"],
        "load_from_db": False,
        "trace_as_input": True,
        "trace_as_metadata": True,
    }


def encode_handle(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True).replace('"', "œ")


def edge(source, source_type, source_output, output_types, target, target_type, field, input_types, field_type):
    source_handle = {"dataType": source_type, "id": source, "name": source_output, "output_types": output_types}
    target_handle = {"fieldName": field, "id": target, "inputTypes": input_types, "type": field_type}
    source_str = encode_handle(source_handle)
    target_str = encode_handle(target_handle)
    return {
        "source": source,
        "target": target,
        "sourceHandle": source_str,
        "targetHandle": target_str,
        "data": {
            "sourceHandle": source_handle,
            "targetHandle": target_handle,
            "sourceType": source_type,
            "targetType": target_type,
        },
        "id": f"xy-edge__{source}{source_str}-{target}{target_str}",
        "animated": False,
        "className": "",
        "style": {"stroke": "#555"},
    }


def ensure_google_variable(token: str, google_key: str) -> None:
    if not google_key:
        print("AVISO: no hay GEMINI_API_KEY en minetwin-ai/.env; configura GOOGLE_API_KEY en Langflow a mano.")
        return
    variables = request("GET", "/api/v1/variables/", token) or []
    existing = next((v for v in variables if v.get("name") == "GOOGLE_API_KEY"), None)
    payload = {"name": "GOOGLE_API_KEY", "value": google_key, "type": "Credential", "default_fields": ["api_key"]}
    if existing:
        payload["id"] = existing["id"]
        request("PATCH", f"/api/v1/variables/{existing['id']}", token, payload)
        print("variable GOOGLE_API_KEY actualizada")
    else:
        request("POST", "/api/v1/variables/", token, payload)
        print("variable GOOGLE_API_KEY creada")


def build_graph(catalog: dict) -> dict:
    agent_cat = find_component(catalog, "models_and_agents", "Agent")
    prompt_cat = find_component(catalog, "models_and_agents", "Prompt Template", "Prompt")
    chat_in_cat = find_component(catalog, "input_output", "ChatInput")
    chat_out_cat = find_component(catalog, "input_output", "ChatOutput")
    google_cat = find_component(catalog, "google", "ext:google:GoogleGenerativeAIComponent@official", "GoogleGenerativeAIModel")

    def mt(name: str) -> dict:
        return find_component(catalog, "minetwin", f"ext:minetwin:{name}@extra", name)

    gemini_values = {"model_name": GEMINI_MODEL, "tool_model_enabled": True, "temperature": 0.2}
    # stream=False: con Gemini, el streaming del Agent solo conserva el primer fragmento de texto
    # cuando el modelo escribe, llama una herramienta y sigue escribiendo (respuesta truncada).
    agent_values = {
        "add_calculator_tool": False,
        "add_current_date_tool": False,
        "max_iterations": 12,
        "n_messages": 20,
        "stream": False,
    }

    nodes = [
        clone_node(mt("UploadProcedureFile"), "UploadProcedureFile-mt", "UploadProcedureFile", "Upload Procedure File", {"x": -420, "y": 760}),
        clone_node(mt("ProcedureLoader"), "ProcedureLoader-mt", "ProcedureLoader", "Procedure Loader", {"x": -420, "y": 80}, field_values={"domain": "TODOS"}),
        clone_node(mt("LogbookLoader"), "LogbookLoader-mt", "LogbookLoader", "Logbook Loader", {"x": -420, "y": 420}, field_values={"limit": 20}),
        clone_node(prompt_cat, "Prompt-main", "Prompt Template", "Prompt Copiloto", {"x": 60, "y": 0}, field_values={"template": MAIN_AGENT_TEMPLATE}),
        clone_node(prompt_cat, "Prompt-report", "Prompt Template", "Prompt Informe", {"x": 60, "y": 420}, field_values={"template": REPORT_TEMPLATE}),
        clone_node(google_cat, "Gemini-report", "GoogleGenerativeAIModel", "Gemini Informe", {"x": 520, "y": 300}, field_values=gemini_values),
        clone_node(mt("TwinStateTool"), "TwinStateTool-report", "TwinStateTool", "Consultar gemelo (informe)", {"x": 520, "y": 700}, tool_mode=True),
        clone_node(
            agent_cat,
            "Agent-ShiftReport",
            "Agent",
            "Informe de Turno",
            {"x": 980, "y": 420},
            tool_mode=True,
            description=(
                "Genera el informe de turno de la mina con KPIs vivos del gemelo, eventos de la bitácora y "
                "procedimientos. Úsala cuando pidan un informe, reporte o resumen del turno."
            ),
            field_values={**agent_values, "system_prompt": ""},
        ),
        clone_node(mt("TwinStateTool"), "TwinStateTool-mt", "TwinStateTool", "Consultar gemelo", {"x": 980, "y": -420}, tool_mode=True),
        clone_node(mt("KuzRamTool"), "KuzRamTool-mt", "KuzRamTool", "Calcular Kuz-Ram", {"x": 980, "y": -220}, tool_mode=True),
        clone_node(mt("WhatIfTool"), "WhatIfTool-mt", "WhatIfTool", "Simular escenario", {"x": 980, "y": -20}, tool_mode=True),
        clone_node(mt("ExplainDrlTool"), "ExplainDrlTool-mt", "ExplainDrlTool", "Explicar recomendación DRL", {"x": 980, "y": 180}, tool_mode=True),
        clone_node(mt("ProposeActionTool"), "ProposeActionTool-mt", "ProposeActionTool", "Proponer acción (HITL)", {"x": 980, "y": 900}, tool_mode=True),
        clone_node(mt("LogbookEntryTool"), "LogbookEntryTool-mt", "LogbookEntryTool", "Registrar en bitácora", {"x": 980, "y": 1100}, tool_mode=True),
        clone_node(google_cat, "Gemini-main", "GoogleGenerativeAIModel", "Gemini Copiloto", {"x": 1480, "y": -120}, field_values=gemini_values),
        clone_node(
            agent_cat,
            "Agent-Copilot",
            "Agent",
            "Copiloto MineTwin",
            {"x": 1480, "y": 200},
            description="Copiloto operacional de mina a planta conectado al gemelo digital de MineTwin.",
            field_values={**agent_values, "system_prompt": ""},
        ),
        clone_node(chat_in_cat, "ChatInput-mt", "ChatInput", "Chat Input", {"x": 980, "y": 1320}),
        clone_node(chat_out_cat, "ChatOutput-mt", "ChatOutput", "Chat Output", {"x": 1980, "y": 280}),
    ]

    by_id = {node["id"]: node for node in nodes}
    by_id["Prompt-main"]["data"]["node"]["template"]["procedimientos"] = prompt_variable_field("procedimientos")
    for var in ("procedimientos", "bitacora"):
        by_id["Prompt-report"]["data"]["node"]["template"][var] = prompt_variable_field(var)

    for node in nodes:
        template = node["data"]["node"].get("template") or {}
        api_key = template.get("api_key")
        if node["data"]["type"] == "GoogleGenerativeAIModel" and isinstance(api_key, dict):
            # La clave vive en la variable global de Langflow, nunca en el JSON del flujo.
            api_key.update({"load_from_db": True, "value": "GOOGLE_API_KEY", "password": True})

    message_in = ["Message", "Text"]
    edges = [
        edge("ProcedureLoader-mt", "ProcedureLoader", "output", ["Message"], "Prompt-main", "Prompt Template", "procedimientos", message_in, "str"),
        edge("ProcedureLoader-mt", "ProcedureLoader", "output", ["Message"], "Prompt-report", "Prompt Template", "procedimientos", message_in, "str"),
        edge("LogbookLoader-mt", "LogbookLoader", "output", ["Message"], "Prompt-report", "Prompt Template", "bitacora", message_in, "str"),
        edge("Prompt-main", "Prompt Template", "prompt", ["Message"], "Agent-Copilot", "Agent", "system_prompt", ["Message"], "str"),
        edge("Prompt-report", "Prompt Template", "prompt", ["Message"], "Agent-ShiftReport", "Agent", "system_prompt", ["Message"], "str"),
        edge("Gemini-report", "GoogleGenerativeAIModel", "model_output", ["LanguageModel"], "Agent-ShiftReport", "Agent", "model", ["LanguageModel"], "model"),
        edge("Gemini-main", "GoogleGenerativeAIModel", "model_output", ["LanguageModel"], "Agent-Copilot", "Agent", "model", ["LanguageModel"], "model"),
        edge("TwinStateTool-report", "TwinStateTool", "component_as_tool", ["Tool"], "Agent-ShiftReport", "Agent", "tools", ["Tool"], "other"),
        edge("ChatInput-mt", "ChatInput", "message", ["Message"], "Agent-Copilot", "Agent", "input_value", ["Message"], "str"),
        edge(
            "Agent-Copilot", "Agent", "response", ["Message"], "ChatOutput-mt", "ChatOutput", "input_value",
            ["Data", "JSON", "DataFrame", "Table", "Message"], "other",
        ),
    ]
    for tool_id, tool_type in (
        ("TwinStateTool-mt", "TwinStateTool"),
        ("KuzRamTool-mt", "KuzRamTool"),
        ("WhatIfTool-mt", "WhatIfTool"),
        ("ExplainDrlTool-mt", "ExplainDrlTool"),
        ("ProposeActionTool-mt", "ProposeActionTool"),
        ("LogbookEntryTool-mt", "LogbookEntryTool"),
        ("Agent-ShiftReport", "Agent"),
    ):
        edges.append(edge(tool_id, tool_type, "component_as_tool", ["Tool"], "Agent-Copilot", "Agent", "tools", ["Tool"], "other"))

    return {"nodes": nodes, "edges": edges, "viewport": {"x": 300, "y": 300, "zoom": 0.45}}


# Nombre y descripción que ve el agente principal para cada acción de un nodo en modo herramienta.
# El Agent en modo herramienta expone dos acciones genéricas; solo se deja activa la de texto.
TOOL_OVERRIDES = {
    "Agent-ShiftReport": {
        "Call_Agent_message_response": {
            "name": "generar_informe_turno",
            "description": (
                "Genera el informe de turno de la mina con KPIs vivos del gemelo, eventos de la bitácora y "
                "procedimientos. Úsala cuando pidan un informe, reporte o resumen del turno. "
                "input_value: el pedido del usuario."
            ),
        },
        "Call_Agent_json_response": {"status": False},
    },
}


def attach_tools_metadata(token: str, data: dict) -> None:
    """Pide a Langflow el campo tools_metadata (lo que hace el editor al activar Tool Mode)."""
    for node in data["nodes"]:
        component = node["data"]["node"]
        if not component.get("tool_mode"):
            continue
        body = {
            "code": component["template"]["code"]["value"],
            "template": component["template"],
            "field": "tool_mode",
            "field_value": True,
            "tool_mode": True,
        }
        updated = request("POST", "/api/v1/custom_component/update", token, body)
        field = (updated or {}).get("template", {}).get("tools_metadata")
        if not field:
            print(f"AVISO: Langflow no devolvió tools_metadata para {node['id']}")
            continue
        overrides = TOOL_OVERRIDES.get(node["id"], {})
        for action in field.get("value") or []:
            tag = (action.get("tags") or [action.get("name")])[0]
            action.update(overrides.get(tag, {}))
        component["template"]["tools_metadata"] = field


def find_existing_flow(token: str):
    flows = request("GET", "/api/v1/flows/?get_all=true&header_flows=true", token) or []
    if isinstance(flows, dict):
        flows = flows.get("items") or flows.get("flows") or []
    return next((f for f in flows if f.get("endpoint_name") == ENDPOINT_NAME or f.get("name") == FLOW_NAME), None)


def export_flow(flow: dict) -> Path:
    safe = copy.deepcopy(flow)
    for node in (safe.get("data") or {}).get("nodes") or []:
        template = ((node.get("data") or {}).get("node") or {}).get("template") or {}
        api_key = template.get("api_key")
        if isinstance(api_key, dict) and not api_key.get("load_from_db"):
            api_key["value"] = ""
    out = LANGFLOW_DIR / "flows" / "minetwin-copilot.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> None:
    try:
        token = login()
    except Exception as exc:
        raise SystemExit(f"No se pudo conectar con Langflow en {BASE}: {exc}. ¿Levantaste el docker-compose?")

    ensure_google_variable(token, load_env_value("GEMINI_API_KEY") or load_env_value("GOOGLE_API_KEY"))
    catalog = request("GET", "/api/v1/all", token)
    data = build_graph(catalog)
    attach_tools_metadata(token, data)

    existing = find_existing_flow(token)
    if existing:
        flow = request("PATCH", f"/api/v1/flows/{existing['id']}", token, {"data": data, "endpoint_name": ENDPOINT_NAME})
        print("flujo actualizado", flow.get("id"))
    else:
        projects = request("GET", "/api/v1/projects/", token) or []
        payload = {
            "name": FLOW_NAME,
            "description": "Copiloto operacional de mina a planta conectado al gemelo digital de MineTwin AI.",
            "icon": "Pickaxe",
            "icon_bg_color": "#F59E0B",
            "gradient": "2",
            "data": data,
            "is_component": False,
            "endpoint_name": ENDPOINT_NAME,
        }
        if projects:
            payload["folder_id"] = projects[0]["id"]
        flow = request("POST", "/api/v1/flows/", token, payload)
        print("flujo creado", flow.get("id"))

    print("endpoint:", f"{BASE}/api/v1/run/{ENDPOINT_NAME}")
    print("exportado en", export_flow(flow))


if __name__ == "__main__":
    sys.exit(main())
