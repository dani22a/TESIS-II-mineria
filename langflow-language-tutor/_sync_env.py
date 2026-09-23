from pathlib import Path

env_path = Path(r"D:\UNIVERSIDAD\CICLO X\TESIS II\langflow-language-tutor\.env")
lines = env_path.read_text(encoding="utf-8").splitlines()
key = ""
for line in lines:
    if line.startswith("GOOGLE_API_KEY="):
        key = line.split("=", 1)[1].strip()
if not any(line.startswith("GEMINI_API_KEY=") for line in lines):
    out = []
    for line in lines:
        out.append(line)
        if line.startswith("GOOGLE_API_KEY="):
            out.append(f"GEMINI_API_KEY={key}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("added GEMINI_API_KEY alias, key_len", len(key.strip().strip('\"')))
else:
    print("GEMINI_API_KEY already present")
