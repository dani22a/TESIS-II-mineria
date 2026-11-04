"""Local BM25 retriever over authorized markdown docs. No embeddings, no external calls."""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STOP = set("a an and are as at be by for from has have in is it of on or that the this to was were what "
           "which with how do does should can about into than then their there these those".split())
INSUFFICIENT = "Insufficient evidence in the authorized documents to answer this question."


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 1]


@dataclass
class Chunk:
    source: str
    heading: str
    text: str
    tf: Counter


class Retriever:
    def __init__(self, docs_dir: Path, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.chunks: list[Chunk] = []
        for path in sorted(Path(docs_dir).glob("*.md")):
            heading = path.stem
            for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8")):
                block = block.strip()
                if not block:
                    continue
                if block.startswith("#") and "\n" not in block:
                    heading = block.lstrip("# ")
                    continue
                self.chunks.append(Chunk(path.name, heading, block, Counter(tokens(block))))
        n = max(len(self.chunks), 1)
        self.avg = max(sum(sum(c.tf.values()) for c in self.chunks) / n, 1)
        df = Counter(t for c in self.chunks for t in c.tf)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _score(self, q: list[str], c: Chunk) -> float:
        length = sum(c.tf.values())
        s = 0.0
        for t in set(q):
            f = c.tf.get(t, 0)
            if f:
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg))
        return s

    def search(self, query: str, k: int = 3, min_coverage: float = 0.5, min_score: float = 1.0) -> dict:
        q = tokens(query)
        if not q or not self.chunks:
            return {"answer": INSUFFICIENT, "sufficient": False, "sources": []}
        ranked = sorted(((self._score(q, c), c) for c in self.chunks), key=lambda x: -x[0])[:k]
        hits = []
        for score, c in ranked:
            coverage = len(set(q) & set(c.tf)) / len(set(q))  # share of query terms found in the chunk
            if score >= min_score and coverage >= min_coverage:
                hits.append({"source": c.source, "section": c.heading, "score": round(score, 3),
                             "coverage": round(coverage, 2), "excerpt": c.text[:600]})
        if not hits:
            return {"answer": INSUFFICIENT, "sufficient": False, "sources": []}
        answer = "Based on the authorized documents (placeholders until replaced): " + hits[0]["excerpt"]
        return {"answer": answer, "sufficient": True, "sources": hits}
