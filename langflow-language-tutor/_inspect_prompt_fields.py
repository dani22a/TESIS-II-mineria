import json
from pathlib import Path

samples = json.loads(Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_sample_flows.json").read_text(encoding="utf-8"))
blog = next(f for f in samples if f["name"] == "Blog Writer")
simple = next(f for f in samples if f["name"] == "Simple Agent")

prompt_node = next(n for n in blog["data"]["nodes"] if n["id"].startswith("Prompt"))
tmpl = prompt_node["data"]["node"]["template"]
print("PROMPT TEMPLATE KEYS", list(tmpl.keys()))
for k,v in tmpl.items():
    if k == "code":
        continue
    if isinstance(v, dict):
        print("\nFIELD", k)
        print(" display", v.get("display_name"), "type", v.get("type"), "input_types", v.get("input_types"), "value", (v.get("value") if not isinstance(v.get("value"), str) or len(str(v.get("value")))<120 else str(v.get("value"))[:120]))
        print(" extra", {kk:v.get(kk) for kk in ["list","required","show","advanced","dynamic","name","load_from_db","trace_as_input","info"]})

print("\n\n==== SIMPLE AGENT URL node template keys (tool mode) ====")
url = next(n for n in simple["data"]["nodes"] if "URL" in n["id"])
print("tool_mode", url["data"]["node"].get("tool_mode"))
print("outputs", json.dumps(url["data"]["node"].get("outputs"), indent=2)[:1500])
print("node keys", [k for k in url["data"]["node"].keys() if k != "template"])

print("\n==== SIMPLE AGENT edge sourceHandle raw ====")
for e in simple["data"]["edges"]:
    print(e["source"], "->", e["target"])
    print(" sourceHandle", e.get("sourceHandle")[:180] if isinstance(e.get("sourceHandle"), str) else e.get("sourceHandle"))
    print(" targetHandle", e.get("targetHandle")[:180] if isinstance(e.get("targetHandle"), str) else e.get("targetHandle"))
