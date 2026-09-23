import json
import gzip
import urllib.request
from pathlib import Path

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]

req = urllib.request.Request(
    base + "/api/v1/flows/",
    headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Accept-Encoding": "identity"},
)
with urllib.request.urlopen(req, timeout=60) as r:
    raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    flows = json.loads(raw)

for item in flows:
    name = item.get("name") or ""
    print(f"{name!r}  id={item.get('id')} nodes={len((item.get('data') or {}).get('nodes') or [])}")

# dump Multi Agent and any Simple
wanted = []
for item in flows:
    n = (item.get("name") or "").lower()
    if "simple" in n or "multi agent" in n or "blog writer" in n:
        wanted.append(item)

out = Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_sample_flows.json")
# Keep only lightweight metadata + first flow full
dump = []
for item in wanted:
    dump.append(item)
out.write_text(json.dumps(dump, ensure_ascii=False), encoding="utf-8")
print("dumped", len(dump), "to sample")
