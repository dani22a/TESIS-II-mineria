import json
from pathlib import Path

data = json.loads(Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_all_components.json").read_text(encoding="utf-8"))
agent = data["models_and_agents"]["Agent"]
prompt = data["models_and_agents"]["Prompt Template"]
addword = data["language_tutor"]["ext:language_tutor:AddWordTool@extra"]

print("=== AGENT extra keys ===")
for k in sorted(agent.keys()):
    if k not in {"template", "code"}:
        v = agent[k]
        if not isinstance(v, (dict, list)) or (isinstance(v, list) and len(v) < 8):
            print(k, ":", v if not isinstance(v, str) or len(v)<200 else v[:200])
        else:
            print(k, type(v).__name__, len(v) if hasattr(v,"__len__") else "")

print("\n=== AGENT outputs full ===")
print(json.dumps(agent.get("outputs"), indent=2)[:4000])
print("\n=== AGENT tool_mode related ===")
for k,v in agent.items():
    if "tool" in k.lower() or "legacy" in k.lower() or "output_types" in k.lower():
        print(k, json.dumps(v)[:500] if not isinstance(v,str) else v[:300])

print("\n=== ADDWORD keys ===")
for k in sorted(addword.keys()):
    if k not in {"template"}:
        v = addword[k]
        s = json.dumps(v) if not isinstance(v,str) else v
        print(k, s[:300])

print("\n=== PROMPT keys ===")
for k in sorted(prompt.keys()):
    if k not in {"template"}:
        v = prompt[k]
        s = json.dumps(v) if not isinstance(v,str) else v
        print(k, s[:400])
