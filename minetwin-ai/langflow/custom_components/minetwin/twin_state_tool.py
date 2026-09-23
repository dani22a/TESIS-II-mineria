from langflow.custom import Component
from langflow.io import Output
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


class TwinStateTool(Component):
    display_name = "Consultar gemelo"
    description = (
        "Consulta el estado vivo del gemelo digital de MineTwin: producción total (t/h), colas por pala, "
        "camiones en cola, nivel de tolva del chancador, rendimiento y energía del molino SAG. "
        "Úsala para cualquier pregunta sobre cómo está la mina ahora."
    )
    icon = "radar"
    name = "TwinStateTool"

    inputs = []
    outputs = [
        Output(display_name="Estado del gemelo", name="output", method="consultar_estado_gemelo"),
    ]

    def consultar_estado_gemelo(self) -> Message:
        data = _call_minetwin("query_twin_state", {}, _session_id(self))
        text = json.dumps(data, ensure_ascii=False)
        self.status = text[:500]
        return Message(text=text)
