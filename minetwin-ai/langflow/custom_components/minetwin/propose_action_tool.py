from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Message

import json
import os
import urllib.error
import urllib.request


def _session_id(component) -> str | None:
    try:
        return component.graph.session_id
    except Exception:
        return None


def _candidate_urls() -> list[str]:
    # MINETWIN_API_URL admite varias URLs separadas por coma (start.ps1 pone las IPs de Windows).
    configured = [url.strip().rstrip("/") for url in os.getenv("MINETWIN_API_URL", "").split(",") if url.strip()]
    defaults = ["http://host.containers.internal:3000", "http://host.docker.internal:3000"]
    return configured + [url for url in defaults if url not in configured]


def _call_minetwin(tool: str, payload: dict, session_id: str | None) -> dict:
    body = json.dumps({**payload, "session_id": session_id}).encode("utf-8")
    failures = []
    for base in _candidate_urls():
        request = urllib.request.Request(
            f"{base}/api/twin/tools/{tool}",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {"error": f"MineTwin respondió {exc.code}: {detail[:300]}"}
        except Exception as exc:
            failures.append(f"{base} ({exc})")
    return {"error": "No se pudo conectar con MineTwin (¿npm run dev está corriendo?). Probado: " + "; ".join(failures)}


class ProposeActionTool(Component):
    display_name = "Proponer acción (HITL)"
    description = (
        "Genera una propuesta de acción operativa que queda PENDIENTE de aprobación humana en MineTwin. "
        "No ejecuta nada por sí misma. Tipos: 'dispatch' (reasignar camiones entre palas), "
        "'blast' (ajustar factor de carga con Kuz-Ram), 'crusher' (priorizar mineral hacia el chancador). "
        "Úsala solo cuando el usuario pida proponer, reasignar, aplicar o ejecutar una acción."
    )
    icon = "shield-check"
    name = "ProposeActionTool"

    inputs = [
        MessageTextInput(
            name="kind",
            display_name="Tipo de acción",
            info="Uno de: dispatch, blast, crusher.",
            tool_mode=True,
            value="dispatch",
        ),
    ]
    outputs = [
        Output(display_name="Propuesta", name="output", method="proponer_accion"),
    ]

    def proponer_accion(self) -> Message:
        payload = {"kind": str(self.kind or "dispatch").strip().lower()}
        data = _call_minetwin("propose_action", payload, _session_id(self))
        text = json.dumps(data, ensure_ascii=False)
        self.status = text[:500]
        return Message(text=text)
