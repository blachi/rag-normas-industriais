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
    r"^\s*(?:(\d{1,2}(?:\.\d{1,3}){1,5})\.?\s*[-–]?\s+(?=\S)"
    r"|(GLOSS[ÁA]RIO|ANEXO\s+[IVX]+|REFER[ÊE]NCIAS(?:\s+BIBLIOGR[ÁA]FICAS)?|BIBLIOGRAFIA)\b)",
    re.M,
)
# inicio de definicao em glossario, numerado ("1. Alta Tensao (AT): ") ou nao ("Barreira: ").
# Cada NR formata o glossario de um jeito; o separador nao pode depender de um formato so.
TERMO = re.compile(r"(?:^|(?<=[.;]))\s*(?:\d{1,3}[.)]\s*)?([A-ZÀ-Ú][^.:;()]{1,80}(?:\([^)]{1,15}\))?)\s*:\s")
NAO_E_TERMO = {"Observação", "Obs", "Nota", "Fonte", "Exemplo", "Exemplos",
               "Acesso em", "Disponível em"}   # os dois ultimos sao de referencia bibliografica
REVOGADO = re.compile(r"\(\s*revogad[oa]", re.I)
VERBO_NORMATIVO = re.compile(
    r"\b(deve|devem|deverá|deverão|é|são|será|serão|pode|podem|poderá|compete|cabe|cabem|"
    r"vedad[oa]s?|proibid[oa]s?|obrigatóri[oa]s?|aplica|aplicam|considera|consideram|estabelece|fica|ficam)\b",
    re.I,
)
# numero no inicio da linha que NAO e item: remissao quebrada no PDF
# ("...conforme o item\n12.4.7 e seus subitens, desta NR..."). Sem isso, 16 trechos abriam um
# item falso no meio da frase e a resposta citava o item errado (achado em 29/10).
REMISSAO_ANTES = re.compile(r"\b(?:itens?|subitens?|alíneas?)\s*$", re.I)
REMISSAO_DEPOIS = re.compile(r"(?:e seus subitens|desta NR|deste Anexo|do Anexo|da NR|e \d|,)", re.I)
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
    t = re.sub(r"^.*\.{5,}.*$", "", t, flags=re.M)  # linha de sumario ("OBJETIVO ....... 3")
    return t


def _definicoes(corpo: str) -> list[tuple[str, str]]:
    """Separa um glossario em (termo, definicao). Sem termo reconhecido, devolve o bloco inteiro."""
    inicios = [m for m in TERMO.finditer(corpo) if m.group(1).strip() not in NAO_E_TERMO]
    if len(inicios) < 2:
        return [("", corpo)]
    saida = []
    if inicios[0].start() > 0 and corpo[:inicios[0].start()].strip():
        saida.append(("", corpo[:inicios[0].start()].strip()))
    for a, b in zip(inicios, inicios[1:] + [None]):
        saida.append((a.group(1).strip(), corpo[a.start():b.start() if b else len(corpo)].strip()))
    return saida


def _paginas(pdf: Path) -> list[tuple[int, str]]:
    r = PdfReader(str(pdf))
    paginas = [(i + 1, _limpa(p.extract_text() or "")) for i, p in enumerate(r.pages)]
    return _sem_cabecalho_rodape(paginas)


def _sem_cabecalho_rodape(paginas: list[tuple[int, str]], fracao: float = 0.3) -> list[tuple[int, str]]:
    """Remove linhas que se repetem em muitas paginas (cabecalho/rodape).

    A NR-33 traz em toda pagina "Entra em vigor no dia 03 de outubro de 2022 ... Este texto nao
    substitui o publicado no DOU"; o rodape caia no meio dos itens da PET e do vigia e os
    embeddings desses itens passavam a falar de vigencia. Vale para qualquer PDF.
    """
    if len(paginas) < 4:
        return paginas
    from collections import Counter
    norm = lambda s: " ".join(s.split())
    conta = Counter(l for _, t in paginas for l in {norm(x) for x in t.splitlines()} if len(norm(l)) >= 15)
    repetidas = {l for l, c in conta.items() if c >= max(3, fracao * len(paginas))}
    return [(n, "\n".join(x for x in t.splitlines() if norm(x) not in repetidas)) for n, t in paginas]


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
    anexo = ""   # dentro de um anexo a numeracao e PROPRIA dele ("Anexo III, item 12.1" nao e o item 12.1 da NR)

    def fecha():
        nonlocal secao
        if item and buf:
            corpo = " ".join(" ".join(buf).split())
            if not corpo:
                return
            # titulo de secao: vira contexto dos itens seguintes, nao trecho proprio.
            # NR-10 escreve "10.5 SEGURANCA EM ..." (maiusculas); NR-12/33 escrevem
            # "12.1 Princípios gerais" / "33.5.13 Sinalização de segurança". So o 1o formato era
            # reconhecido, e os titulos da NR-12/33 viravam ~50 trechos-lixo no indice.
            # Curto e SEM verbo de obrigacao = titulo; "As PETs emitidas devem ser rastreáveis." fica.
            curto_sem_verbo = len(corpo) <= 60 and not VERBO_NORMATIVO.search(corpo)
            nucleo = item.split(", item ")[-1]     # "Anexo X, item 4.1" -> "4.1"
            if nucleo[0].isdigit() and len(corpo) <= TITULO_MAX and (corpo.upper() == corpo or curto_sem_verbo):
                secao = f"{item} {corpo}".strip()
                return
            if item == "Glossário":
                # uma definicao por trecho: cada termo e enderecavel sozinho, como um item
                rotulados = [(f"Glossário: {termo}" if termo else "Glossário", d) for termo, d in _definicoes(corpo)]
            else:
                rotulados = [(item, corpo)]
            # NENHUM trecho escapa do limite de tamanho, qualquer que seja o rotulo
            pedacos = [(rotulo, parte) for rotulo, txt in rotulados for parte in _quebra(txt)]
            for rotulo, parte in pedacos:
                trechos.append(Trecho(
                    # sequencial no DOCUMENTO: o mesmo numero de item reaparece (texto e anexo,
                    # texto e comentario do manual); um contador por item gerava IDs repetidos
                    id=f"{meta['norma']}|{rotulo}|{len(trechos)}",
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
            sai_do_anexo = False
            if m.group(1):
                numero = m.group(1)
                if REMISSAO_ANTES.search(texto[max(0, m.start() - 30):m.start()]) or \
                        REMISSAO_DEPOIS.match(texto, m.end()):
                    continue
                if anexo and numero.split(".")[0] == prefixo and numero.count(".") >= 2:
                    # "ANEXO I" citado no meio do texto (o manual da NR-35 faz isso cedo) abria o
                    # modo anexo e engolia 35.1.2, 35.3.2...: item de 3 niveis com o prefixo da NR
                    # e o texto principal voltando. Os anexos numeram com 2 niveis ("12.1" do Anexo III).
                    anexo, sai_do_anexo = "", True
                elif anexo:
                    # 107 trechos de anexo da NR-12 saiam como "item 12.4.3" do texto principal
                    numero = f"{anexo}, item {numero}"
                elif numero.split(".")[0] != prefixo:
                    continue
            else:   # "GLOSSÁRIO" -> "Glossário"; "ANEXO II" -> "Anexo II"; "REFERÊNCIAS" -> "Referências"
                bruto = " ".join(m.group(2).split()).upper()
                if bruto.startswith("GLOSS"):
                    numero = "Glossário"
                elif bruto.startswith("ANEXO"):
                    numero = "Anexo " + bruto.split()[1]
                else:
                    numero = "Referências"
                anexo = numero if numero.startswith("Anexo") else ""
            buf.append(texto[pos:m.start()])
            fecha()                       # fecha o item ANTERIOR com a secao dele
            if sai_do_anexo:
                secao = ""
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
