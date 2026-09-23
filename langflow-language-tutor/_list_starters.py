import json
import gzip
import urllib.request
from pathlib import Path

base = "http://127.0.0.1:7860"
with urllib.request.urlopen(base + "/api/v1/auto_login", timeout=30) as r:
    token = json.loads(r.read())["access_token"]

def get(path):
    req = urllib.request.Request(
        base + path,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw)

for path in ["/api/v1/starter-projects", "/api/v1/flows/", "/api/v1/projects/"]:
    try:
        data = get(path)
        print("\n====", path, type(data).__name__, len(data) if hasattr(data, "__len__") else "")
        if isinstance(data, list):
            for item in data[:15]:
                if isinstance(item, dict):
                    print(" -", item.get("name") or item.get("id"), item.get("description", "")[:80] if item.get("description") else item.get("id"))
        elif isinstance(data, dict):
            print(list(data.keys())[:20])
    except Exception as e:
        print(path, e)
