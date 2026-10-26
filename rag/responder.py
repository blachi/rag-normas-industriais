"""Resposta com citacao, avisos e recusa.

Tres regras que valem mais que a fluencia do texto:
1. toda afirmacao sai com norma + item + pagina;
2. item revogado ou norma com texto novo gera AVISO explicito;
3. abaixo do limiar de similaridade a resposta e "nao encontrei", nunca um palpite.

Geracao com LLM e opcional: com ANTHROPIC_API_KEY no ambiente, o Claude redige a resposta
usando SO os trechos recuperados; sem a chave, a resposta e extrativa (os trechos citados).
"""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

from rag import busca

# Medido em 26/10/2026: 25 perguntas do gabarito -> 1o resultado com similaridade minima 0,847;
# 8 perguntas fora do assunto -> maxima 0,822. O limiar fica no meio da folga. A folga e
# ESTREITA (0,025) e foi medida na mesma amostra: e um limiar provisorio, nao calibrado.
LIMIAR = 0.835
K = 5


@dataclass
class Resposta:
    pergunta: str
    encontrou: bool
    texto: str
    fontes: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


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
    desde = _catalogo().get(t.get("documento", ""), {}).get("vigente_desde")
    return not desde or hoje >= dt.date.fromisoformat(desde)


def busca_vigente(pergunta: str, k: int = K, hoje: dt.date | None = None) -> list[tuple[dict, float]]:
    """Semantica + vigencia: busca 3k e poe na frente o texto que VALE na data.

    Sem isso, com a NR-10 nova (vale so em 01/06/2027) no indice, o texto que ainda nao
    vale vinha em 1o lugar em 10 de 25 perguntas. A redacao futura continua na lista,
    depois, com aviso: quem planeja a adequacao precisa ve-la.
    """
    hoje = hoje or dt.date.today()
    achados = busca.semantica(pergunta, k * 3)
    return sorted(achados, key=lambda ts: not _vale_hoje(ts[0], hoje))[:k]   # sort estavel


def responde(pergunta: str, k: int = K, limiar: float = LIMIAR) -> Resposta:
    achados = busca_vigente(pergunta, k)
    fontes = [{**t, "similaridade": round(s, 3)} for t, s in achados if s >= limiar]
    if not fontes:
        melhor = round(achados[0][1], 3) if achados else None
        return Resposta(pergunta, False,
                        f"Não encontrei nas normas indexadas um trecho que responda a isso (melhor similaridade {melhor}, limiar {limiar}).")
    if os.environ.get("ANTHROPIC_API_KEY"):
        texto = _gera_com_claude(pergunta, fontes)
    else:
        f = fontes[0]
        texto = f"{f['texto']}\n— {f['norma']}, item {f['item']} (p. {f['pagina']})"
    return Resposta(pergunta, True, texto, fontes, _avisos(fontes))
