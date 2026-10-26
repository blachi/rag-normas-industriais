"""Resposta com citacao, avisos e recusa.

Tres regras que valem mais que a fluencia do texto:
1. toda afirmacao sai com norma + item + pagina;
2. item revogado ou norma com texto novo gera AVISO explicito;
3. abaixo do limiar de similaridade a resposta e "nao encontrei", nunca um palpite.

Geracao com LLM e opcional: com ANTHROPIC_API_KEY no ambiente, o Claude redige a resposta
usando SO os trechos recuperados; sem a chave, a resposta e extrativa (os trechos citados).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

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


def _avisos(fontes: list[dict]) -> list[str]:
    av = []
    for f in fontes:
        if f.get("revogado"):
            av.append(f"{f['norma']} item {f['item']} está REVOGADO — não use como obrigação vigente.")
    normas = {f["norma"] for f in fontes}
    for f in fontes:
        if "substituído" in f.get("vigencia", "") or "texto novo" in f.get("vigencia", ""):
            av.append(f"{f['norma']}: {f['vigencia']}.")
            break
    if any(n.startswith("NR-10") for n in normas):
        av.append("A NR-10 tem texto novo (Portaria MTE nº 737/2026): confira a vigência antes de aplicar.")
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


def responde(pergunta: str, k: int = K, limiar: float = LIMIAR) -> Resposta:
    achados = busca.semantica(pergunta, k)
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
