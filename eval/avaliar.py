"""Mede os tres buscadores contra o gabarito de eval/perguntas.jsonl.

Metricas por buscador:
  acerto@1  - o item certo veio em 1o lugar
  acerto@5  - o item certo esta entre os 5 primeiros (o que a geracao vai ler)
  MRR       - media de 1/posicao do item certo (0 se nao veio nos 5)

Tambem confere se, quando o item certo esta revogado, o trecho chega marcado como
revogado (para a resposta poder avisar em vez de citar norma morta).

Uso:  python -m eval.avaliar            (gera eval/resultado.json e eval/RESULTADO.md)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from rag import busca

AQUI = Path(__file__).resolve().parent
K = 5


def _posicao(resultados, itens_certos) -> int | None:
    for i, (t, _) in enumerate(resultados, start=1):
        # gabarito "Glossário: Alta Tensão" casa com o rotulo do trecho da definicao
        if t["item"] in itens_certos or any(t["item"].startswith(c) for c in itens_certos if c.startswith("Glossário")):
            return i
    return None


def avalia() -> dict:
    perguntas = [json.loads(l) for l in (AQUI / "perguntas.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    trechos = busca.carrega_trechos()
    bm25 = busca.BM25(trechos)
    metodos = {
        "bm25": lambda q: bm25.busca(q, K),
        "semantica": lambda q: busca.semantica(q, K),
        "hibrida": lambda q: busca.hibrida(q, bm25, K),
    }
    saida = {"n_perguntas": len(perguntas), "k": K, "metodos": {}, "detalhe": []}
    por_pergunta = {p["id"]: {"pergunta": p["pergunta"], "certo": p["itens"]} for p in perguntas}

    for nome, f in metodos.items():
        a1 = a5 = 0
        rr = 0.0
        t0 = time.perf_counter()
        aviso_ok = aviso_total = 0
        for p in perguntas:
            res = f(p["pergunta"])
            pos = _posicao(res, set(p["itens"]))
            a1 += pos == 1
            a5 += pos is not None
            rr += 1 / pos if pos else 0.0
            por_pergunta[p["id"]][nome] = {"posicao": pos, "top3": [t["item"] for t, _ in res[:3]]}
            if p.get("espera_aviso_revogado"):
                aviso_total += 1
                if pos and bool(res[pos - 1][0].get("revogado")):
                    aviso_ok += 1
        n = len(perguntas)
        saida["metodos"][nome] = {
            "acerto@1": round(a1 / n, 3),
            "acerto@5": round(a5 / n, 3),
            "MRR": round(rr / n, 3),
            "ms_por_pergunta": round(1000 * (time.perf_counter() - t0) / n, 1),
            "aviso_revogado": f"{aviso_ok}/{aviso_total}",
        }
    saida["detalhe"] = [{"id": k, **v} for k, v in por_pergunta.items()]
    return saida


def relatorio_md(r: dict) -> str:
    linhas = [
        f"# Resultado da avaliação — {r['n_perguntas']} perguntas, top-{r['k']}",
        "",
        "| Buscador | acerto@1 | acerto@5 | MRR | ms/pergunta | aviso de revogado |",
        "|---|---|---|---|---|---|",
    ]
    for nome, m in r["metodos"].items():
        linhas.append(f"| {nome} | {m['acerto@1']:.0%} | {m['acerto@5']:.0%} | {m['MRR']:.3f} | {m['ms_por_pergunta']} | {m['aviso_revogado']} |")
    linhas += ["", "## Onde cada um errou (item certo fora do 1º lugar)", "",
               "| Pergunta | Certo | bm25 | semântica | híbrida |", "|---|---|---|---|---|"]
    for d in r["detalhe"]:
        if all(d[m]["posicao"] == 1 for m in r["metodos"]):
            continue
        cel = [f"{d[m]['posicao'] or '—'} ({', '.join(d[m]['top3'])})" for m in r["metodos"]]
        linhas.append(f"| {d['pergunta']} | {', '.join(d['certo'])} | " + " | ".join(cel) + " |")
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    r = avalia()
    (AQUI / "resultado.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    md = relatorio_md(r)
    (AQUI / "RESULTADO.md").write_text(md, encoding="utf-8")
    print(md)
