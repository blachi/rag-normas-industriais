"""Calibra o limiar de recusa sobre a nota do cross-encoder — e testa em dado separado.

O que conta como erro (e o que NAO conta):
  - responder ERRADO uma pergunta do gabarito (1o trecho mostrado nao e o item certo)  -> erro
  - responder qualquer coisa a uma pergunta FORA do assunto                          -> erro
  - RECUSAR uma pergunta do gabarito que teria sido respondida CERTO                  -> erro
  - recusar uma pergunta do gabarito que seria respondida errado                     -> ACERTO
    ("nao encontrei" e melhor que resposta errada com cara de certa)

A 1a versao exigia "nunca recusar pergunta do gabarito" e escolheu 0,002 — a nota de uma
pergunta cujo trecho certo nem estava entre os candidatos — deixando passar 8 de 20 perguntas
fora do assunto. Esse criterio protegia respostas que ja estavam erradas.

Protocolo:
  1. ESCOLHE o limiar com o gabarito + eval/fora_calibracao.jsonl;
  2. MEDE esse limiar, ja fixo, em eval/fora_do_assunto.jsonl (nao entra na escolha).
Os dois lados do gabarito sao a mesma amostra da avaliacao: a taxa de erro no gabarito e
dentro da amostra; so a de fora do assunto (teste) e fora dela.

Uso:
  python -m eval.calibra            mede tudo (lento: ~80 perguntas no cross-encoder) e escolhe
  python -m eval.calibra --so-escolhe  reusa as notas gravadas em eval/notas_calibracao.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.avaliar import _posicao
from rag.responder import _reranqueia, nota_de_decisao, ordena

AQUI = Path(__file__).resolve().parent
NOTAS = AQUI / "notas_calibracao.json"
GRADE = [round(x * 0.01, 2) for x in range(1, 100)]


def _le(nome: str) -> list[dict]:
    return [json.loads(l) for l in (AQUI / nome).read_text(encoding="utf-8").splitlines() if l.strip()]


CAMPOS = ("item", "norma", "documento", "revogado")


def _certo_em_1o(g: dict, limiar: float) -> bool:
    """O 1o trecho MOSTRADO depende do limiar (relevante e vigente primeiro): recalcula por limiar."""
    rr = [({k: c.get(k) for k in CAMPOS}, c["nota"]) for c in g["candidatos"]]
    return _posicao(ordena(rr, limiar)[:1], set(g["itens"]), g["norma"]) == 1


def mede() -> dict:
    gabarito = []
    for p in _le("perguntas.jsonl"):
        rr = _reranqueia(p["pergunta"])
        gabarito.append({
            "pergunta": p["pergunta"], "itens": p["itens"], "norma": p.get("norma", "NR-10"),
            "nota": nota_de_decisao(rr),
            # todos os candidatos com nota: a ordem mostrada e refeita para CADA limiar da grade
            "candidatos": [{**{k: t.get(k) for k in CAMPOS}, "nota": s} for t, s in rr],
        })
    fora = lambda nome: [{"pergunta": q["pergunta"], "nota": nota_de_decisao(_reranqueia(q["pergunta"]))} for q in _le(nome)]
    notas = {"gabarito": gabarito, "calibracao": fora("fora_calibracao.jsonl"), "teste": fora("fora_do_assunto.jsonl")}
    NOTAS.write_text(json.dumps(notas, ensure_ascii=False, indent=2), encoding="utf-8")
    return notas


def erros(limiar: float, gabarito: list[dict], fora: list[dict]) -> dict:
    responde = lambda x: x["nota"] >= limiar
    certo = [_certo_em_1o(g, limiar) for g in gabarito]
    return {
        "gabarito_respondido_errado": sum(responde(g) and not c for g, c in zip(gabarito, certo)),
        "gabarito_recusado_que_acertaria": sum(not responde(g) and c for g, c in zip(gabarito, certo)),
        "fora_respondida": sum(responde(f) for f in fora),
    }


def escolhe(notas: dict) -> dict:
    tabela = []
    for l in GRADE:
        e = erros(l, notas["gabarito"], notas["calibracao"])
        tabela.append((sum(e.values()), l, e))
    # menor erro total; no empate, o MAIOR limiar (na duvida, recusa)
    total, limiar, e_cal = min(tabela, key=lambda t: (t[0], -t[1]))
    e_teste = erros(limiar, [], notas["teste"])
    res = {
        "limiar": limiar,
        "erros_na_calibracao": e_cal | {"total": total},
        "teste_fora_do_assunto": {
            "n": len(notas["teste"]),
            "respondidas_indevidamente": e_teste["fora_respondida"],
            "nota_maxima": round(max(t["nota"] for t in notas["teste"]), 3),
            "quais": [t["pergunta"] for t in notas["teste"] if t["nota"] >= limiar],
        },
        "gabarito": {
            "n": len(notas["gabarito"]),
            "certo_em_1o_no_limiar": sum(_certo_em_1o(g, limiar) for g in notas["gabarito"]),
            "recusadas": [g["pergunta"] for g in notas["gabarito"] if g["nota"] < limiar],
        },
        "curva": [{"limiar": l, **e, "total": t} for t, l, e in tabela if l in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)],
    }
    return res


if __name__ == "__main__":
    notas = json.loads(NOTAS.read_text(encoding="utf-8")) if "--so-escolhe" in sys.argv else mede()
    res = escolhe(notas)
    (AQUI / "calibracao.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
