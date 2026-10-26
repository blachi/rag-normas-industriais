"""Leitura dos PDFs das NRs e corte em trechos por ITEM da norma.

Cortar por item (10.2.5, 12.38.1 ...) e nao por numero de caracteres tem uma razao
pratica: a resposta precisa citar o item exato, e um trecho que comeca no meio de um
item e termina no meio de outro nao tem item para citar. Itens muito longos sao
subdivididos, sempre carregando o numero do item.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
CATALOGO = RAIZ / "data" / "catalogo.json"
TRECHOS = RAIZ / "data" / "trechos.jsonl"

# um item comeca no inicio da linha: "10.2.5 ", "12.38.1 ", "33.3.2.1 ", "10.2.8 - MEDIDAS..."
# GLOSSARIO e ANEXO tambem abrem bloco proprio: sem isso o glossario inteiro vira parte do
# ultimo item da norma e "o que e alta tensao?" cita o item errado.
ITEM = re.compile(
    r"^\s*(?:(\d{1,2}(?:\.\d{1,3}){1,5})\.?\s*[-–]?\s+(?=\S)|(GLOSS[ÁA]RIO|ANEXO\s+[IVX]+)\b)",
    re.M,
)
REVOGADO = re.compile(r"\(\s*revogad[oa]", re.I)
MAX_CHARS = 1500
TITULO_MAX = 90   # item curto e todo em maiusculas = titulo de secao (ex.: "10.5 SEGURANCA EM ...")


@dataclass
class Trecho:
    id: str
    documento: str
    norma: str
    item: str
    secao: str
    pagina: int
    texto: str
    vigencia: str
    revogado: bool   # o PDF oficial mantem o texto revogado com a nota "(Revogado pela ...)"


def _limpa(t: str) -> str:
    t = t.replace(" ", " ")
    t = re.sub(r"-\n(?=[a-zà-ú])", "", t)          # hifenizacao no fim da linha
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\d{1,3}\s*\n", "\n", t)      # numero de pagina solto
    return t


def _paginas(pdf: Path) -> list[tuple[int, str]]:
    r = PdfReader(str(pdf))
    return [(i + 1, _limpa(p.extract_text() or "")) for i, p in enumerate(r.pages)]


def _quebra(texto: str) -> list[str]:
    """Quebra um item longo em pedacos <= MAX_CHARS, preferindo fim de frase/alinea."""
    if len(texto) <= MAX_CHARS:
        return [texto]
    partes, atual = [], ""
    blocos = []
    for bloco in re.split(r"(?<=[.;:])\s+(?=[a-z]\)|[A-ZÀ-Ú])", texto):
        # reserva: bloco sem ponto de quebra natural e maior que o limite -> corta em fim de palavra
        while len(bloco) > MAX_CHARS:
            corte = bloco.rfind(" ", 0, MAX_CHARS)
            corte = corte if corte > 0 else MAX_CHARS
            blocos.append(bloco[:corte])
            bloco = bloco[corte:].lstrip()
        blocos.append(bloco)
    for bloco in blocos:
        if len(atual) + len(bloco) + 1 > MAX_CHARS and atual:
            partes.append(atual.strip())
            atual = ""
        atual += " " + bloco
    if atual.strip():
        partes.append(atual.strip())
    return partes


def corta(documento: str, meta: dict) -> list[Trecho]:
    pdf = RAW / documento
    prefixo = str(meta["prefixo_item"])          # "10" para NR-10: descarta numeros que nao sao itens
    trechos: list[Trecho] = []
    item, pagina_item, buf = None, 1, []
    secao = ""

    def fecha():
        nonlocal secao
        if item and buf:
            corpo = " ".join(" ".join(buf).split())
            if not corpo:
                return
            if len(corpo) <= TITULO_MAX and corpo.upper() == corpo:
                secao = f"{item} {corpo}".strip()     # titulo: vira contexto dos itens seguintes
                return
            if item == "Glossário":
                # uma definicao por trecho ("1. Alta Tensão (AT): ..."): cada termo e
                # enderecavel sozinho, como um item da norma
                pedacos = [(f"Glossário: {m.group(1).strip()}", m.group(0).strip())
                           for m in re.finditer(r"\d{1,2}\.\s*([^:]{2,80}):.*?(?=\s\d{1,2}\.\s*[A-ZÀ-Ú][^:]{1,80}:|$)", corpo)]
            else:
                pedacos = [(item, parte) for parte in _quebra(corpo)]
            for k, (rotulo, parte) in enumerate(pedacos):
                trechos.append(Trecho(
                    id=f"{meta['norma']}|{rotulo}|{k}",
                    documento=documento,
                    norma=meta["norma"],
                    item=rotulo,
                    secao=secao,
                    pagina=pagina_item,
                    texto=parte,
                    vigencia=meta["vigencia"],
                    revogado=bool(REVOGADO.search(corpo)),
                ))

    for pagina, texto in _paginas(pdf):
        pos = 0
        for m in ITEM.finditer(texto):
            if m.group(1):
                numero = m.group(1)
                if numero.split(".")[0] != prefixo:
                    continue
            else:   # "GLOSSÁRIO" -> "Glossário"; "ANEXO II" -> "Anexo II"
                bruto = " ".join(m.group(2).split())
                numero = "Glossário" if bruto.upper().startswith("GLOSS") else "Anexo " + bruto.split()[1]
            buf.append(texto[pos:m.start()])
            fecha()                       # fecha o item ANTERIOR com a secao dele
            if m.group(2):
                secao = numero
            item, pagina_item, buf = numero, pagina, []
            pos = m.end()
        buf.append(texto[pos:])
    fecha()
    return trechos


def main() -> None:
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    todos: list[Trecho] = []
    for doc, meta in catalogo.items():
        if not (RAW / doc).exists():
            print(f"  falta o arquivo: {doc} (pulado)")
            continue
        t = corta(doc, meta)
        print(f"  {meta['norma']:<10} {doc:<45} {len(t):>4} trechos")
        todos.extend(t)
    with TRECHOS.open("w", encoding="utf-8") as f:
        for t in todos:
            f.write(json.dumps(asdict(t), ensure_ascii=False) + "\n")
    print(f"total: {len(todos)} trechos -> {TRECHOS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
