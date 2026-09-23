import json
import urllib.request
from pathlib import Path

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    tokens = json.loads(r.read())
token = tokens["access_token"]
req = urllib.request.Request(
    base + "/api/v1/all",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    },
)
with urllib.request.urlopen(req, timeout=120) as r:
    raw = r.read()
    print("content-encoding", r.headers.get("Content-Encoding"), "len", len(raw))
    if raw[:2] == b"\x1f\x8b":
        import gzip
        raw = gzip.decompress(raw)
    data = json.loads(raw)

out = Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_all_components.json")
out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
print("top_type", type(data).__name__)
if isinstance(data, dict):
    print("top_keys", list(data.keys())[:40])
    for k, v in data.items():
        if isinstance(v, dict):
            names = list(v.keys())[:30]
            print("cat", k, "n", len(v), "sample", names[:15])
        else:
            print("cat", k, type(v).__name__)
