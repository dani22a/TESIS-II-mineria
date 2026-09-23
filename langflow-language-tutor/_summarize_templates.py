import json
from pathlib import Path

data = json.loads(Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_all_components.json").read_text(encoding="utf-8"))

wanted = {
    "models_and_agents": ["Agent", "Prompt Template", "LanguageModelComponent"],
    "input_output": ["ChatInput", "ChatOutput"],
    "google": ["ext:google:GoogleGenerativeAIComponent@official"],
    "language_tutor": [
        "ext:language_tutor:AddWordTool@extra",
        "ext:language_tutor:UploadWordFile@extra",
        "ext:language_tutor:WordLoader@extra",
    ],
}

def summarize(comp):
    tmpl = (comp.get("template") or {})
    outs = comp.get("outputs") or []
    fields = []
    for name, field in tmpl.items():
        if name.startswith("_") or name == "code":
            continue
        if not isinstance(field, dict):
            continue
        fields.append({
            "name": name,
            "display": field.get("display_name"),
            "type": field.get("type"),
            "input_types": field.get("input_types"),
            "tool_mode": field.get("tool_mode"),
            "show": field.get("show"),
            "value": field.get("value") if not isinstance(field.get("value"), str) or len(str(field.get("value"))) < 80 else str(field.get("value"))[:80],
            "options": field.get("options")[:12] if isinstance(field.get("options"), list) else field.get("options"),
        })
    return {
        "display_name": comp.get("display_name"),
        "name": comp.get("name"),
        "base_classes": comp.get("base_classes"),
        "outputs": [{"name": o.get("name"), "display": o.get("display_name"), "types": o.get("types") or o.get("selected")} for o in outs],
        "fields": fields,
        "icon": comp.get("icon"),
        "description": (comp.get("description") or "")[:200],
    }

summary = {}
for cat, names in wanted.items():
    summary[cat] = {}
    for name in names:
        if name in data[cat]:
            summary[cat][name] = summarize(data[cat][name])
        else:
            summary[cat][name] = "MISSING"

Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_templates_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("wrote summary")
