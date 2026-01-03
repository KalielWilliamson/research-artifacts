from __future__ import annotations

import hashlib
from collections.abc import Iterable

from alphaflow.cognition.memory.ports import EmbeddingsClientPort


class DeterministicEmbeddingsClient(EmbeddingsClientPort):
    """Deterministic embeddings for repeatable evaluation."""

    def __init__(self, *, dim: int = 16) -> None:
        self._dim = max(4, int(dim))

    def embed(self, text: str, *, model: str | None = None) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for idx in range(self._dim):
            byte = digest[idx % len(digest)]
            values.append(float(byte) / 255.0)
        return values


def mean_embedding(vectors: Iterable[list[float]]) -> list[float]:
    vecs = [v for v in vectors if v]
    if not vecs:
        return []
    dim = len(vecs[0])
    sums = [0.0] * dim
    for vec in vecs:
        for idx in range(dim):
            sums[idx] += vec[idx]
    return [val / len(vecs) for val in sums]
