"""Resumable download of the NLM Shenzhen and Montgomery TB chest X-ray sets (public, no credentials).

Each image is streamed into memory, hashed (sha256 of the ORIGINAL bytes), converted to grayscale,
resized to SIZExSIZE and stored as PNG. Originals are never written to disk. Re-running skips images
that are already stored (resume) and retries transient failures with exponential backoff.

  python scripts/download_data.py --out data/real --size 256 --workers 4
  python scripts/download_data.py --out data/real --only montgomery --limit 5   # quick check

Citation: Jaeger S, et al. Two public chest X-ray datasets for computer-aided screening of pulmonary
diseases. Quant Imaging Med Surg 2014;4(6):475-477. NIH OHSRP exemption 5357 (see DATA_DICTIONARY.md).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BASE = "https://data.lhncbc.nlm.nih.gov/public/Tuberculosis-Chest-X-ray-Datasets/"
SETS = {
    "shenzhen": {"url": BASE + "Shenzhen-Hospital-CXR-Set/", "prefix": "CHNCXR",
                 "institution": "shenzhen_no3_hospital_china"},
    "montgomery": {"url": BASE + "Montgomery-County-CXR-Set/MontgomerySet/", "prefix": "MCUCXR",
                   "institution": "montgomery_county_usa"},
}
UA = {"User-Agent": "tb-screening-thesis/1.0 (academic research; polite sequential client)"}


def get(url: str, tries: int = 6, stream_bytes: bool = True, timeout: int = 90) -> bytes:
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception as e:  # noqa: BLE001 - retry on any transport error
            last = e
            time.sleep(min(60, 2 ** k))
    raise RuntimeError(f"download failed after {tries} tries: {url}: {last}")


def list_images(key: str) -> list[str]:
    html = get(SETS[key]["url"] + "CXR_png/index.html").decode("utf-8", "replace")
    names = sorted(set(re.findall(rf"href='({SETS[key]['prefix']}_\d+_[01]\.png)'", html)))
    return [n[:-4] for n in names]


def parse_reading(text: str) -> dict:
    """Shenzhen: 'male 45yrs\n<finding>'. Montgomery: "Patient's Sex: F \nPatient's Age: 027Y\n<finding>"."""
    sex = age = None
    m = re.search(r"\b(male|female)\b", text, re.I)
    if m:
        sex = m.group(1).lower()[0].upper()
    m2 = re.search(r"Sex:\s*([MF])", text, re.I)
    if m2:
        sex = m2.group(1).upper()
    a = re.search(r"(\d{1,3})\s*yrs", text, re.I) or re.search(r"Age:\s*0*(\d{1,3})\s*Y", text, re.I)
    if a:
        age = int(a.group(1))
    lines = [ln.strip() for ln in text.strip().splitlines()]
    finding = " ".join(ln for ln in lines[1:] if ln and not ln.lower().startswith("patient's age")) \
        if len(lines) > 1 else ""
    return {"sex": sex, "age": age, "finding_text": finding}


def process(key: str, image_id: str, out: Path, size: int) -> dict:
    meta_p = out / "meta" / f"{image_id}.json"
    img_p = out / key / f"{image_id}.png"
    if meta_p.exists() and img_p.exists():
        return json.loads(meta_p.read_text())
    raw = get(SETS[key]["url"] + f"CXR_png/{image_id}.png")
    sha = hashlib.sha256(raw).hexdigest()
    im = Image.open(io.BytesIO(raw))
    w, h = im.size
    mode = im.mode
    im.load()
    if im.mode in ("I;16", "I", "F"):  # 16/32-bit gray: scale to 8-bit
        import numpy as np
        a = np.asarray(im, dtype=np.float32)
        a = (a - a.min()) / max(a.max() - a.min(), 1.0) * 255
        im = Image.fromarray(a.astype("uint8"))
    im = im.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    img_p.parent.mkdir(parents=True, exist_ok=True)
    tmp = img_p.with_suffix(".tmp")
    im.save(tmp, format="PNG")
    tmp.replace(img_p)
    try:
        rd = parse_reading(get(SETS[key]["url"] + f"ClinicalReadings/{image_id}.txt").decode("utf-8", "replace"))
    except RuntimeError:
        rd = {"sex": None, "age": None, "finding_text": ""}
    stored_sha = hashlib.sha256(img_p.read_bytes()).hexdigest()
    meta = {"image_id": image_id, "dataset": key, "label": int(image_id.endswith("_1")),
            "institution": SETS[key]["institution"], "sha256": sha, "sha256_stored": stored_sha,
            "orig_width": w, "orig_height": h, "orig_mode": mode, **rd,
            "image_path": f"{key}/{image_id}.png"}
    meta_p.parent.mkdir(parents=True, exist_ok=True)
    meta_p.write_text(json.dumps(meta))
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/real"))
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", choices=list(SETS), default=None)
    ap.add_argument("--limit", type=int, default=None, help="first N images per set (testing)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows, failed = [], []
    for key in ([a.only] if a.only else list(SETS)):
        ids = list_images(key)[: a.limit]
        print(f"{key}: {len(ids)} images listed", flush=True)
        done = 0
        with ThreadPoolExecutor(a.workers) as ex:
            futs = {ex.submit(process, key, i, a.out, a.size): i for i in ids}
            for f in as_completed(futs):
                try:
                    rows.append(f.result())
                except Exception as e:  # noqa: BLE001
                    failed.append((futs[f], str(e)))
                done += 1
                if done % 25 == 0:
                    print(f"  {key}: {done}/{len(ids)} (failed {len(failed)})", flush=True)
    df = pd.DataFrame(rows)
    df["patient_id"] = df["image_id"].str.extract(r"_(\d+)_[01]$")[0].radd(df["dataset"].str[:3] + "_")
    n0 = len(df)
    df = df.sort_values("image_id").drop_duplicates("sha256", keep="first")  # dedupe by original-content hash
    df = df.drop(columns=["orig_mode"]).reset_index(drop=True)
    cols = ["image_id", "patient_id", "dataset", "label", "sex", "age", "institution", "sha256",
            "sha256_stored", "orig_width", "orig_height", "finding_text", "image_path"]
    df[cols].to_csv(a.out / "manifest.csv", index=False)
    print(f"manifest: {len(df)} rows ({n0 - len(df)} hash duplicates removed) -> {a.out / 'manifest.csv'}")
    print(df.groupby(["dataset", "label"]).size().to_string())
    if failed:
        print(f"FAILED {len(failed)} images (re-run to resume):", file=sys.stderr)
        for i, e in failed[:20]:
            print("  ", i, e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
