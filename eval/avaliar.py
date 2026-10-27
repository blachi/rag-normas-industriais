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
from rag.responder import _reranqueia, busca_reranqueada, busca_vigente, nota_de_decisao

AQUI = Path(__file__).resolve().parent
K = 5


def _posicao(resultados, itens_certos, norma="NR-10") -> int | None:
    # o gabarito aponta o texto VIGENTE: o mesmo numero de item na redacao que ainda nao vale nao conta
    for i, (t, _) in enumerate(resultados, start=1):
        if t["norma"] != norma:
            continue
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
        "semantica+vigencia": lambda q: busca_vigente(q, K),
    }
    # com a norma escolhida por quem pergunta (seletor na tela): mede o ganho de tirar a
    # confusao ENTRE normas. Precisa da norma da pergunta, entao entra a parte.
    familia_de = {p["pergunta"]: busca.familia(p.get("norma", "NR-10")) for p in perguntas}
    metodos["com norma escolhida"] = lambda q: busca_vigente(q, K, familia=familia_de[q])
    metodos["reranqueada"] = lambda q: busca_reranqueada(q, K)
    metodos["reranqueada + norma escolhida"] = lambda q: busca_reranqueada(q, K, familia=familia_de[q])
    saida = {"n_perguntas": len(perguntas), "k": K, "metodos": {}, "detalhe": []}
    por_pergunta = {p["id"]: {"pergunta": p["pergunta"], "certo": p["itens"], "norma": p.get("norma", "NR-10")} for p in perguntas}

    for nome, f in metodos.items():
        a1 = a5 = 0
        rr = 0.0
        t0 = time.perf_counter()
        aviso_ok = aviso_total = 0
        for p in perguntas:
            res = f(p["pergunta"])
            pos = _posicao(res, set(p["itens"]), p.get("norma", "NR-10"))
            a1 += pos == 1
            a5 += pos is not None
            rr += 1 / pos if pos else 0.0
            por_pergunta[p["id"]][nome] = {
                "posicao": pos,
                "top3": [t["item"] + ("*" if t["norma"] != p.get("norma", "NR-10") else "") for t, _ in res[:3]],
            }
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
    saida["recusa"] = mede_recusa(perguntas)
    return saida


FINAL = "reranqueada"   # o caminho que o sistema usa de verdade (rag.responder.responde)


def mede_recusa(perguntas: list[dict]) -> dict:
    """Nota do 1o resultado: perguntas do gabarito x perguntas FORA do assunto de TESTE.

    eval/fora_do_assunto.jsonl nao entra na escolha do limiar (eval/calibra.py usa
    eval/fora_calibracao.jsonl): aqui ele so mede. Duas notas lado a lado:
    a similaridade do embedding (como era) e a relevancia do cross-encoder (como e).
    """
    from rag.responder import LIMIAR
    fora = [json.loads(l)["pergunta"] for l in (AQUI / "fora_do_assunto.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    dentro = [p["pergunta"] for p in perguntas]

    def tabela(nota, limiares):
        nd, nf = [nota(q) for q in dentro], [nota(q) for q in fora]
        return {
            "dentro_min": round(min(nd), 3), "fora_max": round(max(nf), 3),
            "linhas": [{"limiar": l,
                        "recusa_indevida": f"{sum(s < l for s in nd)}/{len(nd)}",
                        "aceita_fora_do_assunto": f"{sum(s >= l for s in nf)}/{len(nf)}"} for l in limiares],
        }

    # a relevancia do cross-encoder ja foi medida por eval/calibra.py (mesma funcao de decisao,
    # mesmas perguntas); refazer custaria ~60 consultas de ~15 s. Notas mais velhas que o
    # indice nao valem: ai mede de novo.
    notas_arq = AQUI / "notas_calibracao.json"
    indice = busca.CHROMA / "chroma.sqlite3"
    if notas_arq.exists() and indice.exists() and notas_arq.stat().st_mtime > indice.stat().st_mtime:
        notas = json.loads(notas_arq.read_text(encoding="utf-8"))
        cache = {n["pergunta"]: n["nota"] for grupo in ("gabarito", "teste") for n in notas[grupo]}
        nota_ce = lambda q: cache[q] if q in cache else nota_de_decisao(_reranqueia(q))
    else:
        nota_ce = lambda q: nota_de_decisao(_reranqueia(q))   # a grandeza da decisao
    return {
        "limiar_em_uso": LIMIAR,
        "similaridade_e5": tabela(lambda q: busca_vigente(q, 1)[0][1], (0.82, 0.835, 0.85, 0.86)),
        "relevancia_cross_encoder": tabela(nota_ce, sorted({0.01, 0.05, 0.1, 0.3, 0.5, LIMIAR})),
    }


def relatorio_md(r: dict) -> str:
    linhas = [
        f"# Resultado da avaliação — {r['n_perguntas']} perguntas, top-{r['k']}",
        "",
        "| Buscador | acerto@1 | acerto@5 | MRR | ms/pergunta | aviso de revogado |",
        "|---|---|---|---|---|---|",
    ]
    for nome, m in r["metodos"].items():
        linhas.append(f"| {nome} | {m['acerto@1']:.0%} | {m['acerto@5']:.0%} | {m['MRR']:.3f} | {m['ms_por_pergunta']} | {m['aviso_revogado']} |")
    por_norma = {}
    for d in r["detalhe"]:
        n = d.get("norma", "NR-10")
        a = por_norma.setdefault(n, [0, 0, 0])
        a[0] += 1
        a[1] += d[FINAL]["posicao"] == 1
        a[2] += d[FINAL]["posicao"] is not None
    linhas += ["", f"## Por norma ({FINAL}, o caminho em uso)", "",
               "| Norma | perguntas | acerto@1 | acerto@5 |", "|---|---|---|---|"]
    for n, (q, a1, a5) in por_norma.items():
        linhas.append(f"| {n} | {q} | {a1}/{q} | {a5}/{q} |")

    # cabecalho gerado a partir dos metodos: antes era fixo em 3 colunas e as linhas tinham 5+
    nomes = list(r["metodos"])
    linhas += ["", f"## Onde o caminho em uso ({FINAL}) errou", "",
               "Posição do item certo (— = fora dos 5) e os 3 primeiros trazidos. "
               "`*` = trecho de outra redação/norma que não a do gabarito.", "",
               "| Pergunta | Certo | " + " | ".join(nomes) + " |", "|---|---|" + "---|" * len(nomes)]
    for d in r["detalhe"]:
        if d[FINAL]["posicao"] == 1:
            continue
        cel = [f"{d[m]['posicao'] or '—'} ({', '.join(d[m]['top3'])})" for m in nomes]
        linhas.append(f"| {d['pergunta']} | {', '.join(d['certo'])} | " + " | ".join(cel) + " |")

    rc = r["recusa"]
    linhas += ["", "## Recusa — testada em 20 perguntas fora do assunto que NÃO entraram na calibração", "",
               f"Limiar em uso: **{rc['limiar_em_uso']}** sobre a relevância do cross-encoder (escolhido em `eval/calibra.py`)."]
    for titulo, chave in (("Como era: similaridade do embedding", "similaridade_e5"),
                          ("Como é: relevância do cross-encoder", "relevancia_cross_encoder")):
        t = rc[chave]
        linhas += ["", f"**{titulo}** — gabarito: mínima {t['dentro_min']} · fora do assunto: máxima {t['fora_max']}", "",
                   "| Limiar | Pergunta boa recusada | Fora do assunto aceita |", "|---|---|---|"]
        linhas += [f"| {x['limiar']} | {x['recusa_indevida']} | {x['aceita_fora_do_assunto']} |" for x in t["linhas"]]
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    r = avalia()
    (AQUI / "resultado.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    md = relatorio_md(r)
    (AQUI / "RESULTADO.md").write_text(md, encoding="utf-8")
    print(md)
