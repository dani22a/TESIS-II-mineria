"""Reconstruye el generador anterior al pase de redacción Q1."""
import json
from pathlib import Path

TRANSCRIPT = Path(
    r"C:\Users\daniel\.cursor\projects\d-UNIVERSIDAD-CICLO-X-TESIS-II"
    r"\agent-transcripts\ce7df3df-77d8-47ac-b3e5-a4fe2d797f46"
    r"\ce7df3df-77d8-47ac-b3e5-a4fe2d797f46.jsonl"
)
HERE = Path(__file__).resolve().parent
OUT_PY = HERE / "manuscrito_antigua.py"

text = None
edits = []
for i, line in enumerate(TRANSCRIPT.open(encoding="utf-8"), 1):
    if "manuscrito.py" not in line:
        continue
    obj = json.loads(line)
    content = obj.get("message", {}).get("content", [])
    if not isinstance(content, list):
        continue
    for block in content:
        if block.get("type") != "tool_use":
            continue
        name = block.get("name")
        inp = block.get("input", {})
        path = str(inp.get("path", ""))
        if "manuscrito.py" not in path:
            continue
        if name == "Write" and text is None:
            text = inp["contents"]
            print("write", i, len(text))
        elif name == "StrReplace":
            old = inp["old_string"]
            new = inp["new_string"]
            edits.append((i, old, new))
            print("edit", i, "old", len(old), "new", len(new))

if text is None:
    raise SystemExit("no se encontro el manuscrito original")

# El pase Q1 empieza en el reemplazo que introduce "Puntos clave".
cut = None
for n, (i, old, new) in enumerate(edits):
    if "Puntos clave" in new or "La radiografía de tórax sigue siendo la puerta" in new:
        cut = n
        break
if cut is None:
    raise SystemExit("no se encontro el inicio de la reescritura")

applied = 0
for i, old, new in edits[:cut]:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"reemplazo ambiguo en linea {i}: {count}")
    text = text.replace(old, new, 1)
    applied += 1

old_out = 'OUT = HERE / "Tamizaje_TB_SP-02_manuscrito.docx"'
new_out = 'OUT = HERE / "Tamizaje_TB_SP-02_version_antigua.docx"'
if old_out not in text:
    raise SystemExit("no se encontro la ruta de salida")
text = text.replace(old_out, new_out, 1)
OUT_PY.write_text(text, encoding="utf-8")
print("applied", applied, "of", cut, "kept; skipped", len(edits) - cut)
print("wrote", OUT_PY)
