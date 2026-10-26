# Assistente de Normas Regulamentadoras (RAG)

Pergunta em português de chão de fábrica, resposta com **norma, item e página**, aviso
quando o item está **revogado** ou a norma tem **texto novo**, e **recusa** quando não
encontra — em vez de inventar.

```
> Posso trabalhar no painel usando aliança e relógio?
É vedado o uso de adornos pessoais nos trabalhos com instalações elétricas ou em suas proximidades.
— NR-10, item 10.2.9.3 (p. 3)
⚠ A NR-10 tem texto novo (Portaria MTE nº 737/2026): confira a vigência antes de aplicar.
```

Python · sentence-transformers (`multilingual-e5-small`) · ChromaDB · FastAPI · pytest.
Roda inteiro no notebook, sem GPU e sem custo de API. Geração com Claude é opcional.

---

## O que foi medido (e o que surpreendeu)

25 perguntas escritas **com palavras diferentes das da norma** ("aliança e relógio" em vez de
"adornos pessoais"), cada uma com o item correto conferido no texto oficial
([`eval/perguntas.jsonl`](eval/perguntas.jsonl)). `python -m eval.avaliar` reproduz.

Índice com as **duas redações da NR-10** (a de 2019, vigente, e a da Portaria MTE nº 737/2026,
que só vale a partir de 01/06/2027). O certo, hoje, é o item do texto vigente.

| Buscador | acerto em 1º | acerto nos 5 primeiros | MRR |
|---|---|---|---|
| Palavra-chave (BM25, sem modelo) | 24% | 48% | 0,33 |
| Semântica (embeddings e5) | 52% | 88% | 0,67 |
| Híbrida (BM25 + semântica, RRF) | 36% | 68% | 0,49 |
| **Semântica + vigência na data** | **76%** | **92%** | **0,82** |

**1. A híbrida perdeu para a semântica pura.** É o contrário da receita comum. Aqui quem pergunta
não usa o vocabulário da norma, então a perna de palavra-chave traz trechos errados para cima
e a fusão os mantém.

**2. Duas versões da mesma norma derrubam qualquer buscador.** Com a nova NR-10 no índice, o
texto que ainda não vale vinha em 1º lugar em 10 de 25 perguntas. A correção não é de modelo,
é de domínio: pôr na frente o que vale **na data** e avisar quando a redação muda — com a data
exata, tirada da própria portaria ("entra em vigor 1 ano após a publicação", DOU 01/06/2026).

**Erros que continuam** (estão no relatório, não escondidos): "posso usar aliança e relógio?"
não acha o 10.2.9.3 ("adornos pessoais") — o modelo pequeno não liga as duas palavras.
Detalhe por pergunta, com o que cada buscador trouxe: [`eval/RESULTADO.md`](eval/RESULTADO.md).

### Três defeitos que a medição achou (e que passariam em qualquer demo)

1. **Glossário grudado no último item.** O PDF não marca o glossário como item; o corte o
   anexava ao 10.14.6, e "o que é alta tensão?" citava o item errado. Agora cada definição é
   um trecho próprio.
2. **Item revogado continua no PDF oficial.** O 10.13.1 traz "(Revogado pela Portaria SEPRT
   nº 915/2019)" mas o texto segue lá. Um RAG ingênuo o cita como obrigação. Aqui o trecho é
   marcado e a resposta avisa.
3. **Item longo sem pontuação de quebra não era dividido.** O teste
   `test_quebra_respeita_tamanho` pegou; corte de reserva em fim de palavra.

### Limiar de recusa: medido, e com a ressalva escrita

Similaridade do 1º resultado: perguntas do gabarito ≥ **0,847**; perguntas fora do assunto
(bolo, Copa, passagem) ≤ **0,822**. O limiar ficou em 0,835. A folga é estreita (0,025) e foi
medida na mesma amostra — é provisório. Para calibrar de verdade: um conjunto separado de
perguntas fora do assunto, maior.

### O que este projeto NÃO mede

- Qualidade do texto gerado pelo LLM (só a recuperação está medida).
- Generalização: 25 perguntas escritas por uma pessoa só. O número certo vem de perguntas
  reais de usuários.
- As outras NRs (12, 33, 35) entram no índice quando os PDFs são adicionados em `data/raw/`;
  o gabarito delas ainda não existe.

---

## Como funciona

```
PDF oficial ──► corte POR ITEM da norma ──► embeddings e5 ──► ChromaDB
                (10.2.5, 10.2.5.1 …;            ("passage:")
                 glossário por termo;
                 marca revogado)
pergunta ──► embedding ("query:") ──► top-5 ──► limiar ──► resposta citada + avisos
                                                  └── abaixo: "não encontrei"
```

Cortar **por item**, e não por número de caracteres, é o que permite citar o item exato.

## Rodar

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m rag.ingest                       # corta os PDFs de data/raw
.venv\Scripts\python -c "from rag import busca; busca.indexa(busca.carrega_trechos())"
.venv\Scripts\python -m eval.avaliar                     # mede os 3 buscadores
.venv\Scripts\python -m pytest -q                        # 8 testes
.venv\Scripts\python -m uvicorn api:app --port 8010      # GET /perguntar?q=...
```

Com `ANTHROPIC_API_KEY` no ambiente, a resposta é redigida pelo Claude usando **só** os
trechos recuperados, com o item citado após cada afirmação.

## Fontes

Textos oficiais do Ministério do Trabalho e Emprego (gov.br), listados com a vigência em
[`data/catalogo.json`](data/catalogo.json). Os PDFs não são redistribuídos aqui.

---

Rafael Blachi · Caçapava/SP
