import gzip, json, urllib.request
from pathlib import Path

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]

req = urllib.request.Request(base+"/api/v1/models", headers={"Authorization": f"Bearer {token}", "Accept-Encoding":"identity"})
with urllib.request.urlopen(req, timeout=30) as r:
    raw = r.read()
    if raw[:2]==b"\x1f\x8b":
        raw = gzip.decompress(raw)
    data = json.loads(raw)

Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\_models.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)[:80000], encoding="utf-8")
print(type(data).__name__)
if isinstance(data, dict):
    print("keys", list(data.keys())[:40])
    for k,v in data.items():
        if isinstance(v, dict):
            print(" ", k, "keys", list(v.keys())[:20])
        elif isinstance(v, list):
            print(" ", k, "len", len(v), "sample", v[:1])
        else:
            print(" ", k, v)
elif isinstance(data, list):
    print("len", len(data))
    print(json.dumps(data[0], indent=2)[:2000] if data else "empty")

req = urllib.request.Request(base+"/api/v1/model-provider-policy", headers={"Authorization": f"Bearer {token}", "Accept-Encoding":"identity"})
with urllib.request.urlopen(req, timeout=30) as r:
    raw = r.read()
    if raw[:2]==b"\x1f\x8b":
        raw = gzip.decompress(raw)
    print("\npolicy", raw[:2000])
