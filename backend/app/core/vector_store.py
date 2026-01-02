from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST_MODEL = True
except Exception:
    SentenceTransformer = None  # type: ignore
    _HAS_ST_MODEL = False

try:
    import faiss
    _HAS_FAISS = True
except Exception:
    faiss = None  # type: ignore
    _HAS_FAISS = False


class FaissVectorStore:
    """Lightweight FAISS-backed vector store with metadata persistence.

    If `data_dir` is None the store remains in-memory and is not persisted.
    The embedder will attempt to use `sentence-transformers` if available,
    otherwise a deterministic hash-based fallback is used (useful for tests).
    """

    def __init__(self, dimension: int = 384, data_dir: Optional[str] = None, model_name: str = "all-MiniLM-L6-v2"):
        self.dim = dimension
        self.data_dir = data_dir
        self._ids: List[int] = []
        self._meta: Dict[str, Dict] = {}

        # Embedding model
        self.model = None
        if _HAS_ST_MODEL:
            try:
                self.model = SentenceTransformer(model_name)
                # override dim with model vector size
                self.dim = self.model.get_sentence_embedding_dimension()
            except Exception:
                self.model = None

        # FAISS index
        if _HAS_FAISS:
            self.index = faiss.IndexFlatIP(self.dim)
        else:
            # fallback: store vectors in numpy array and brute-force search
            self.index = None
            self._vectors = np.zeros((0, self.dim), dtype=np.float32)

        if self.data_dir:
            os.makedirs(self.data_dir, exist_ok=True)
            self._ids_path = os.path.join(self.data_dir, "ids.json")
            self._meta_path = os.path.join(self.data_dir, "meta.json")
            self._vecs_path = os.path.join(self.data_dir, "vecs.npy")
            self._load_persisted()

    def _load_persisted(self):
        if os.path.exists(self._ids_path):
            try:
                with open(self._ids_path, "r", encoding="utf-8") as f:
                    self._ids = json.load(f)
            except Exception:
                self._ids = []
        if os.path.exists(self._meta_path):
            try:
                with open(self._meta_path, "r", encoding="utf-8") as f:
                    self._meta = json.load(f)
            except Exception:
                self._meta = {}
        if _HAS_FAISS and os.path.exists(self._vecs_path):
            try:
                vecs = np.load(self._vecs_path)
                if vecs.shape[1] != self.dim:
                    # ignore persisted if dimension mismatch
                    vecs = None
                else:
                    self.index = faiss.IndexFlatIP(self.dim)
                    # normalize
                    faiss.normalize_L2(vecs)
                    self.index.add(vecs)
            except Exception:
                pass
        elif not _HAS_FAISS and os.path.exists(self._vecs_path):
            try:
                self._vectors = np.load(self._vecs_path)
            except Exception:
                self._vectors = np.zeros((0, self.dim), dtype=np.float32)

    def _persist(self):
        if not self.data_dir:
            return
        with open(self._ids_path, "w", encoding="utf-8") as f:
            json.dump(self._ids, f)
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(self._meta, f)
        if _HAS_FAISS:
            # extract vectors from index
            if self.index is not None and self.index.ntotal > 0:
                vecs = self.index.reconstruct_n(0, self.index.ntotal)  # type: ignore
                np.save(self._vecs_path, vecs)
        else:
            np.save(self._vecs_path, self._vectors)

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        if self.model is not None:
            emb = np.array(self.model.encode(texts, convert_to_numpy=True), dtype=np.float32)
            # normalize for cosine similarity
            norms = np.linalg.norm(emb, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            emb = emb / norms
            return emb

        # fallback deterministic hashing embedding: reproducible, small resource usage
        mats = []
        for t in texts:
            h = np.frombuffer(t.encode("utf-8"), dtype=np.uint8).astype(np.float32)
            vec = np.zeros(self.dim, dtype=np.float32)
            if h.size:
                for i, v in enumerate(h):
                    vec[i % self.dim] += float(v)
            # normalize
            n = np.linalg.norm(vec)
            if n > 0:
                vec /= n
            mats.append(vec)
        return np.vstack(mats)

    def add(self, ticket_id: int, text: str, metadata: Optional[Dict] = None) -> None:
        vec = self._embed_texts([text])
        if _HAS_FAISS:
            if self.index is None:
                import faiss

                self.index = faiss.IndexFlatIP(self.dim)
            self.index.add(vec)
        else:
            self._vectors = np.vstack([self._vectors, vec]) if self._vectors.size else vec
        self._ids.append(ticket_id)
        self._meta[str(ticket_id)] = metadata or {}
        self._persist()

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float, Dict]]:
        if not query or (not _HAS_FAISS and getattr(self, "_vectors", None) is None):
            return []
        qv = self._embed_texts([query])
        if _HAS_FAISS and self.index is not None and self.index.ntotal > 0:
            D, I = self.index.search(qv, min(top_k, self.index.ntotal))  # type: ignore
            # D are inner products because we normalized => cosine
            res = []
            for score, idx in zip(D[0], I[0]):
                tid = self._ids[idx]
                res.append((tid, float(score), self._meta.get(str(tid), {})))
            return res

        # brute force
        if getattr(self, "_vectors", None) is None or self._vectors.shape[0] == 0:
            return []
        sims = np.dot(self._vectors, qv[0])
        idxs = np.argsort(-sims)[:top_k]
        res = []
        for i in idxs:
            tid = self._ids[i]
            res.append((tid, float(sims[i]), self._meta.get(str(tid), {})))
        return res

    def clear(self):
        self._ids = []
        self._meta = {}
        if _HAS_FAISS:
            if self.index is not None:
                self.index.reset()
        else:
            self._vectors = np.zeros((0, self.dim), dtype=np.float32)
        self._persist()
