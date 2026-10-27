"""Reranqueamento com cross-encoder (BAAI/bge-reranker-v2-m3).

Por que existe: o embedding compara pergunta e trecho "de longe" (cada um vira um vetor
sozinho). Com 5 normas no indice isso falhava de dois jeitos medidos:
  - ordem: o item certo da NR-33 nao vinha em 1o em nenhuma de 5 perguntas;
  - recusa: "qual o valor do salario minimo?" casava com "requisitos minimos" da NR-35 e
    nenhum limiar de similaridade separava (7 de 20 perguntas fora do assunto respondidas).
O cross-encoder le a pergunta JUNTO com cada trecho e devolve uma nota de relevancia (0 a 1).
"""
from __future__ import annotations

import ctypes
import os
import sys
from functools import lru_cache

MODELO = "BAAI/bge-reranker-v2-m3"
# O modelo em float32 ocupa ~2,3 GB e o carregamento tem pico acima disso. Com 3,7 GB livres
# o processo MORREU com violacao de acesso (0xC0000005) dentro do from_pretrained — sem
# excecao Python para capturar. Por isso a checagem vem ANTES de carregar.
# (bfloat16 cabe em metade, mas sem suporte nativo na CPU levou 15 s POR PAR: inviavel.)
MEMORIA_MINIMA_GB = 4.0


class MemoriaInsuficiente(RuntimeError):
    pass


def memoria_livre_gb() -> float | None:
    try:
        if sys.platform == "win32":
            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = _MS()
            ms.dwLength = ctypes.sizeof(_MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return ms.ullAvailPhys / 1024 ** 3
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024 ** 3
    except Exception:
        return None   # sem como medir: tenta carregar


@lru_cache(maxsize=1)
def _modelo():
    livre = memoria_livre_gb()
    if livre is not None and livre < MEMORIA_MINIMA_GB:
        raise MemoriaInsuficiente(
            f"{livre:.1f} GB de RAM livres; o reranqueador precisa de {MEMORIA_MINIMA_GB:.0f} GB. "
            "Feche programas (navegador) e tente de novo.")
    from sentence_transformers import CrossEncoder
    return CrossEncoder(MODELO, device="cpu", max_length=512)


def _texto(t: dict) -> str:
    return f"{t['norma']} item {t['item']} ({t.get('secao', '')}). {t['texto']}"


def reordena(pergunta: str, candidatos: list[tuple[dict, float]]) -> list[tuple[dict, float]]:
    """Devolve os mesmos candidatos ordenados pela nota do cross-encoder (0 a 1)."""
    if not candidatos:
        return []
    # batch_size=1: medido 22 s (1) x 25 s (2) x 34 s (4) x 43 s (8) para 20 pares — lote maior
    # so acrescenta padding ate o par mais longo (66 a 383 tokens), sem ganho de paralelismo na CPU
    notas = _modelo().predict([(pergunta, _texto(t)) for t, _ in candidatos], batch_size=1, show_progress_bar=False)
    return sorted(((t, float(n)) for (t, _), n in zip(candidatos, notas)), key=lambda x: -x[1])
