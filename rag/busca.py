"""Tres buscadores sobre os mesmos trechos, para que a escolha seja medida e nao opinada.

- bm25:      palavra-chave (linha de base; sem modelo)
- semantica: embeddings multilingual-e5-small em ChromaDB
- hibrida:   fusao das duas listas por Reciprocal Rank Fusion (RRF)
"""
from __future__ import annotations

import json
import math
import os

# o ChromaDB 0.5 tenta telemetria mesmo com Settings(anonymized_telemetry=False); a variavel corta antes
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRECHOS = RAIZ / "data" / "trechos.jsonl"
CHROMA = RAIZ / "data" / "chroma"
MODELO = "intfloat/multilingual-e5-small"
COLECAO = "normas"

STOP = set("""a o as os de da do das dos e em no na nos nas um uma para por com sem que se
ao aos ou ser deve devem sua seu suas seus como mais quando onde qual quais sao é á à
pelo pela pelos pelas este esta isso esse essa entre sobre""".split())


def carrega_trechos() -> list[dict]:
    return [json.loads(l) for l in TRECHOS.read_text(encoding="utf-8").splitlines() if l.strip()]


def _tokens(t: str) -> list[str]:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [w for w in re.findall(r"[a-z0-9]+", t) if w not in STOP and len(w) > 1]


class BM25:
    def __init__(self, trechos: list[dict], k1: float = 1.5, b: float = 0.75):
        self.trechos = trechos
        self.docs = [_tokens(t["secao"] + " " + t["texto"]) for t in trechos]
        self.k1, self.b = k1, b
        self.media = sum(map(len, self.docs)) / max(1, len(self.docs))
        df = Counter(w for d in self.docs for w in set(d))
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def busca(self, pergunta: str, k: int = 5) -> list[tuple[dict, float]]:
        q = _tokens(pergunta)
        notas = []
        for i, tf in enumerate(self.tf):
            L = len(self.docs[i])
            s = 0.0
            for w in q:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * L / self.media))
            notas.append(s)
        ordem = sorted(range(len(notas)), key=lambda i: -notas[i])[:k]
        return [(self.trechos[i], notas[i]) for i in ordem if notas[i] > 0]


@lru_cache(maxsize=1)
def _modelo():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO, device="cpu")


def _colecao():
    import chromadb
    from chromadb.config import Settings
    cli = chromadb.PersistentClient(path=str(CHROMA), settings=Settings(anonymized_telemetry=False))
    return cli.get_or_create_collection(COLECAO, metadata={"hnsw:space": "cosine"})


def indexa(trechos: list[dict]) -> int:
    """(Re)constroi a colecao inteira. O e5 exige o prefixo 'passage: ' nos documentos."""
    import chromadb
    from chromadb.config import Settings
    cli = chromadb.PersistentClient(path=str(CHROMA), settings=Settings(anonymized_telemetry=False))
    try:
        cli.delete_collection(COLECAO)
    except Exception:
        pass
    col = cli.get_or_create_collection(COLECAO, metadata={"hnsw:space": "cosine"})
    textos = [f"passage: {t['norma']} item {t['item']} ({t['secao']}). {t['texto']}" for t in trechos]
    vetores = _modelo().encode(textos, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    col.add(
        ids=[t["id"] for t in trechos],
        embeddings=[v.tolist() for v in vetores],
        documents=[t["texto"] for t in trechos],
        metadatas=[{k: t[k] for k in ("documento", "norma", "item", "secao", "pagina", "vigencia", "revogado")} for t in trechos],
    )
    return col.count()


def semantica(pergunta: str, k: int = 5) -> list[tuple[dict, float]]:
    col = _colecao()
    v = _modelo().encode([f"query: {pergunta}"], normalize_embeddings=True)[0].tolist()
    r = col.query(query_embeddings=[v], n_results=k)
    saida = []
    for id_, doc, meta, dist in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0]):
        saida.append(({"id": id_, "texto": doc, **meta}, 1 - dist))
    return saida


def hibrida(pergunta: str, bm25: BM25, k: int = 5, profundidade: int = 20, c: int = 60) -> list[tuple[dict, float]]:
    """RRF: soma 1/(c + posicao) de cada lista. Nao precisa calibrar escala entre as notas."""
    nota: dict[str, float] = {}
    por_id: dict[str, dict] = {}
    for lista in (bm25.busca(pergunta, profundidade), semantica(pergunta, profundidade)):
        for pos, (t, _) in enumerate(lista):
            nota[t["id"]] = nota.get(t["id"], 0.0) + 1.0 / (c + pos + 1)
            por_id.setdefault(t["id"], t)
    ordem = sorted(nota, key=lambda i: -nota[i])[:k]
    return [(por_id[i], nota[i]) for i in ordem]
