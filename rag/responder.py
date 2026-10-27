"""Resposta com citacao, avisos e recusa.

Tres regras que valem mais que a fluencia do texto:
1. toda afirmacao sai com norma + item + pagina;
2. item revogado ou norma com texto novo gera AVISO explicito;
3. abaixo do limiar de RELEVANCIA a resposta e "nao encontrei", nunca um palpite.

Caminho: embeddings trazem CANDIDATOS -> cross-encoder da a nota de relevancia ->
texto vigente na frente -> limiar sobre a nota do cross-encoder (nao sobre a similaridade,
que medida nao separava pergunta fora do assunto).

Geracao com LLM e opcional: com ANTHROPIC_API_KEY no ambiente, o Claude redige a resposta
usando SO os trechos recuperados; sem a chave, a resposta e extrativa (os trechos citados).
"""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

from rag import busca, rerank

# Nota do cross-encoder (0 a 1) abaixo da qual responde "nao encontrei". Calibrado em
# 26/10/2026 por eval/calibra.py (menor numero de erros: responder errado, responder pergunta
# fora do assunto, recusar o que acertaria). Na calibracao: 0 de 20 fora do assunto
# respondidas; no TESTE (20 que nao entraram na escolha): 0 de 20, nota maxima 0,055.
# Entre 0,02 e 0,15 o erro total e quase igual; no empate o criterio fica com o maior.
LIMIAR = 0.15
K = 5
# Quantos trechos os embeddings entregam ao cross-encoder. Medido (26/10): o trecho certo
# esta entre os 5/10/15/20/40 primeiros em 30/32/34/34/34 das 40 perguntas — satura em 15.
# Acima disso so custa tempo (~1 s por trecho no cross-encoder neste notebook).
CANDIDATOS = 15


@dataclass
class Resposta:
    pergunta: str
    encontrou: bool
    texto: str
    fontes: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    relevancia_topo: float | None = None   # nota do 1o trecho, tambem quando recusa (vai para o registro)


@lru_cache(maxsize=1)
def _catalogo() -> dict:
    return json.loads((busca.RAIZ / "data" / "catalogo.json").read_text(encoding="utf-8"))


def _br(iso: str) -> str:
    return dt.date.fromisoformat(iso).strftime("%d/%m/%Y")


def _avisos(fontes: list[dict], hoje: dt.date | None = None) -> list[str]:
    """Avisos que dependem da DATA: o mesmo trecho e vigente hoje e deixa de ser amanha."""
    hoje = hoje or dt.date.today()
    av = []
    for f in fontes:
        if f.get("revogado"):
            av.append(f"{f['norma']} item {f['item']} está REVOGADO — não use como obrigação vigente.")
        meta = _catalogo().get(f.get("documento", ""), {})
        desde, ate = meta.get("vigente_desde"), meta.get("vigente_ate")
        if desde and hoje < dt.date.fromisoformat(desde):
            av.append(f"{f['norma']} item {f['item']} é da NOVA redação, que só vale a partir de {_br(desde)}. "
                      f"Até lá, vale o texto anterior.")
        if ate and hoje <= dt.date.fromisoformat(ate):
            av.append(f"{f['norma']}: texto vigente até {_br(ate)}; a redação muda depois dessa data.")
        if ate and hoje > dt.date.fromisoformat(ate):
            av.append(f"{f['norma']} item {f['item']}: este texto deixou de valer em {_br(ate)}.")
        if meta.get("tipo") == "manual":
            av.append(f"{f['norma']}: {meta['vigencia']}.")
    return list(dict.fromkeys(av))


def _gera_com_claude(pergunta: str, fontes: list[dict]) -> str:
    import anthropic

    contexto = "\n\n".join(f"[{f['norma']} item {f['item']}, p.{f['pagina']}]\n{f['texto']}" for f in fontes)
    msg = anthropic.Anthropic().messages.create(
        model=os.environ.get("RAG_MODELO", "claude-opus-4-8"),
        max_tokens=600,
        system=(
            "Você responde perguntas sobre Normas Regulamentadoras usando SOMENTE os trechos fornecidos. "
            "Cite o item entre colchetes após cada afirmação, ex.: [NR-10 item 10.2.7]. "
            "Se os trechos não respondem, diga exatamente: 'Os trechos recuperados não respondem a isso.' "
            "Não use conhecimento externo. Português do Brasil, frases curtas."
        ),
        messages=[{"role": "user", "content": f"Trechos:\n{contexto}\n\nPergunta: {pergunta}"}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _vale_hoje(t: dict, hoje: dt.date) -> bool:
    """Vale hoje = redacao ja em vigor E item nao revogado.

    (A 1a versao so olhava a data da redacao: um item revogado, que nao vale hoje, era
    ordenado como se valesse e aparecia como resposta principal, com o aviso embaixo.)
    """
    if t.get("revogado"):
        return False
    desde = _catalogo().get(t.get("documento", ""), {}).get("vigente_desde")
    return not desde or hoje >= dt.date.fromisoformat(desde)


def normas_da_familia(fam: str) -> list[str]:
    """'NR-10' -> ['NR-10', 'NR-10 (2026)']: escolher a norma traz todas as redacoes dela."""
    return sorted({m["norma"] for m in _catalogo().values() if busca.familia(m["norma"]) == fam})


def busca_vigente(pergunta: str, k: int = K, hoje: dt.date | None = None,
                  familia: str | None = None) -> list[tuple[dict, float]]:
    """Semantica + vigencia: busca 3k e poe na frente o texto que VALE na data.

    Sem isso, com a NR-10 nova (vale so em 01/06/2027) no indice, o texto que ainda nao
    vale vinha em 1o lugar em 10 de 25 perguntas. A redacao futura continua na lista,
    depois, com aviso: quem planeja a adequacao precisa ve-la.
    """
    hoje = hoje or dt.date.today()
    achados = busca.semantica(pergunta, k * 3, normas_da_familia(familia) if familia else None)
    return sorted(achados, key=lambda ts: not _vale_hoje(ts[0], hoje))[:k]   # sort estavel


def _reranqueia(pergunta: str, familia: str | None = None) -> list[tuple[dict, float]]:
    """Embeddings trazem CANDIDATOS; o cross-encoder devolve todos ordenados pela nota (0 a 1)."""
    candidatos = busca.semantica(pergunta, CANDIDATOS, normas_da_familia(familia) if familia else None)
    return rerank.reordena(pergunta, candidatos)


def nota_de_decisao(reranqueados: list[tuple[dict, float]]) -> float:
    """A UNICA nota que decide responder x recusar: a maior relevancia entre os candidatos.

    responde() e eval/calibra.py usam esta mesma funcao. (Antes a calibracao olhava o 1o
    trecho DEPOIS da ordenacao por vigencia — outra grandeza — e o limiar calibrado nao
    valia para a decisao real.)
    """
    return max((s for _, s in reranqueados), default=0.0)


def ordena(reranqueados: list[tuple[dict, float]], limiar: float = LIMIAR,
           hoje: dt.date | None = None) -> list[tuple[dict, float]]:
    """Relevante antes de irrelevante; ENTRE os relevantes, o que vale hoje primeiro; depois a nota.

    A vigencia desempata entre trechos que respondem — nunca poe um trecho irrelevante vigente
    acima de um relevante da redacao nova (que segue na lista, com aviso de data).
    """
    hoje = hoje or dt.date.today()
    return sorted(reranqueados, key=lambda ts: (ts[1] < limiar, not _vale_hoje(ts[0], hoje), -ts[1]))


def busca_reranqueada(pergunta: str, k: int = K, hoje: dt.date | None = None,
                      familia: str | None = None, limiar: float = LIMIAR) -> list[tuple[dict, float]]:
    """O caminho em uso, sem a decisao de recusa: os k trechos na ordem que a resposta mostra."""
    return ordena(_reranqueia(pergunta, familia), limiar, hoje)[:k]


def responde(pergunta: str, k: int = K, limiar: float = LIMIAR, familia: str | None = None) -> Resposta:
    reranqueados = _reranqueia(pergunta, familia)
    melhor = round(nota_de_decisao(reranqueados), 3)
    achados = ordena(reranqueados, limiar)[:k]
    fontes = [{**t, "relevancia": round(s, 3)} for t, s in achados if s >= limiar]
    if melhor < limiar:
        return Resposta(pergunta, False,
                        f"Não encontrei nas normas indexadas um trecho que responda a isso (melhor relevância {melhor}, limiar {limiar}).",
                        relevancia_topo=melhor)
    if os.environ.get("ANTHROPIC_API_KEY"):
        texto = _gera_com_claude(pergunta, fontes)
    else:
        f = fontes[0]
        texto = f"{f['texto']}\n— {f['norma']}, item {f['item']} (p. {f['pagina']})"
    return Resposta(pergunta, True, texto, fontes, _avisos(fontes), relevancia_topo=melhor)
