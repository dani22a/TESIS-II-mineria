import json
from pathlib import Path

samples = json.loads(Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_sample_flows.json").read_text(encoding="utf-8"))

def compact_flow(flow):
    data = flow.get("data") or {}
    nodes = []
    for n in data.get("nodes") or []:
        nd = n.get("data") or {}
        node = nd.get("node") or {}
        tmpl = node.get("template") or {}
        interesting = {}
        for key in ["system_prompt", "agent_llm", "model_name", "model", "api_key", "template", "input_value", "tools", "language"]:
            if key in tmpl and isinstance(tmpl[key], dict):
                val = tmpl[key].get("value")
                interesting[key] = {
                    "value": val if not isinstance(val, str) or len(val) < 160 else val[:160],
                    "tool_mode": tmpl[key].get("tool_mode"),
                    "show": tmpl[key].get("show"),
                    "type": tmpl[key].get("type"),
                    "input_types": tmpl[key].get("input_types"),
                }
        nodes.append({
            "id": n.get("id"),
            "type": n.get("type"),
            "data_type": nd.get("type"),
            "display_name": node.get("display_name") or nd.get("display_name"),
            "tool_mode": node.get("tool_mode"),
            "outputs": [{"name": o.get("name"), "types": o.get("types"), "tool_mode": o.get("tool_mode")} for o in (node.get("outputs") or [])],
            "interesting": interesting,
            "position": n.get("position"),
        })
    edges = []
    for e in data.get("edges") or []:
        edges.append({
            "source": e.get("source"),
            "target": e.get("target"),
            "sourceHandle": e.get("sourceHandle"),
            "targetHandle": e.get("targetHandle"),
            "data": {k: e.get("data", {}).get(k) for k in ["sourceHandle", "targetHandle", "sourceType", "targetType"]} if isinstance(e.get("data"), dict) else None,
        })
    return {"name": flow.get("name"), "id": flow.get("id"), "nodes": nodes, "edges": edges}

out = [compact_flow(f) for f in samples]
Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_sample_compact.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("ok")
