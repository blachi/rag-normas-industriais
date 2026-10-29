# Assistente de Normas Regulamentadoras (RAG)

Pergunta em português de chão de fábrica; resposta com **norma, item e página**; aviso quando o
item está **revogado** ou a norma vai **mudar de redação** (com a data); e **"não encontrei"**
quando as normas não respondem — em vez de inventar.

Saídas reais do sistema, copiadas do terminal (só a quebra de linha foi ajustada; nada cortado):

```
> Um eletricista pode trabalhar sozinho em linha energizada de alta tensão?
Os serviços em instalações elétricas energizadas em AT, bem como aqueles executados no Sistema
Elétrico de Potência - SEP, não podem ser realizados individualmente.
— NR-10, item 10.7.3 (p. 6)
AVISO: NR-10: texto vigente até 31/05/2027; a redação muda depois dessa data.

> O trabalhador pode se recusar a fazer o serviço se achar que corre risco grave?
7. Direito de Recusa: instrumento que assegura ao trabalhador a interrupção de uma atividade de
trabalho por considerar que ela envolve grave e iminente risco para sua segurança e saúde ou de
outras pessoas. 12 8.
— NR-10, item Glossário: Direito de Recusa (p. 11)
AVISO: NR-10: texto vigente até 31/05/2027; a redação muda depois dessa data.
AVISO: NR-35 (manual): é o MANUAL de interpretação de abril de 2018, não o texto legal; a NR-35
foi alterada depois — confira a redação vigente antes de aplicar.
AVISO: NR-10 item 10.14.1 está REVOGADO — não use como obrigação vigente.

> Qual o valor do salário mínimo?
Não encontrei nas normas indexadas um trecho que responda a isso (melhor relevância 0.003, limiar 0.15).
```

No 2º exemplo, o item que trata do direito de recusa (10.14.1) foi **revogado**: a resposta
principal é a definição em vigor, e o item revogado aparece depois, com aviso. O "12 8." no fim é
resto da extração do PDF (número da página e do termo seguinte) — limitação conhecida do corte.

Python · sentence-transformers (`multilingual-e5-small` + cross-encoder `bge-reranker-v2-m3`) ·
ChromaDB · FastAPI · SQLite · pytest · Docker · GitHub Actions. Roda inteiro na CPU, sem custo de API.

---

## Resultado

40 perguntas escritas **com palavras diferentes das da norma** ("posso usar aliança e relógio?"
para um item que fala em "adornos pessoais"), cada uma com o item certo conferido no texto
oficial ([`eval/perguntas.jsonl`](eval/perguntas.jsonl)). O certo é o item do texto **vigente**.
`python -m eval.avaliar` reproduz; o detalhe por pergunta está em [`eval/RESULTADO.md`](eval/RESULTADO.md).

| Caminho | acerto em 1º | acerto nos 5 primeiros |
|---|---|---|
| Palavra-chave (BM25) | 12% | 45% |
| Busca semântica (embeddings) | 38% | 70% |
| Híbrida (BM25 + semântica, RRF) | 22% | 65% |
| Semântica + vigência na data | 50% | 75% |
| **Semântica → cross-encoder → vigência (em uso)** | **68%** | **82%** |

Com ±14 pontos de margem (IC 95% com 40 perguntas), diferenças de poucos pontos entre linhas
não são distinguíveis. Os números caíram 2 a 6 pontos em 29/10 com a correção do item 10 abaixo:
parte dos acertos anteriores vinha de trechos citados com o número de item errado.

E a recusa, testada em 20 perguntas fora do assunto que **não** entraram na escolha do limiar:

| Nota usada para recusar | fora do assunto respondidas |
|---|---|
| Similaridade do embedding (limiar no meio da folga) | 9 de 20 |
| **Relevância do cross-encoder (limiar 0,15)** | **0 de 20** |

"Qual o valor do salário mínimo?" tinha similaridade **0,84** com "requisitos **mínimos**" da
NR-35 — mais alta que muitas perguntas legítimas. Nenhum limiar de similaridade separava; a nota
do cross-encoder, que lê pergunta e trecho juntos, dá **0,003**.

## O que a medição achou (e que passaria em qualquer demo)

Cada um destes tem teste em [`tests/test_rag.py`](tests/test_rag.py).

1. **O índice vetorial devolvia o vizinho errado.** O padrão do ChromaDB (`search_ef=10`)
   divergia da busca exata no 1º resultado em 6 de 40 perguntas — e os números da avaliação
   mudavam de uma rodada para outra. Com ~1.650 trechos não há por que aproximar.
2. **Duas redações da mesma norma.** A NR-10 nova (Portaria MTE nº 737/2026) só vale a partir de
   01/06/2027 — data tirada da própria portaria ("entra em vigor 1 ano após a publicação", DOU
   01/06/2026). Sem tratar vigência, o texto que ainda não vale vinha em 1º em 10 de 25 perguntas.
3. **Item revogado continua no PDF oficial.** 10.13.1, 10.14.1 e 10.14.5 trazem "(Revogado pela
   Portaria SEPRT nº 915/2019)" com o texto inteiro. Revogado conta como "não vale hoje": vai
   para depois do que está em vigor, com aviso.
4. **Rodapé no meio do item.** A NR-33 repete em toda página "Entra em vigor... Este texto não
   substitui o publicado no DOU"; caía no meio dos itens da PET. Linhas repetidas em muitas
   páginas saem.
5. **Glossário de 47 mil caracteres.** O separador de definições só entendia o formato numerado
   da NR-10; o glossário da NR-12 virou um trecho só. Hoje: uma definição por trecho, qualquer
   formato, e nenhum trecho passa do limite.
6. **Títulos virando trecho.** "12.1 Princípios gerais" e "33.5.13 Sinalização de segurança"
   eram indexados como resposta. Texto curto sem verbo de obrigação é título (contexto dos
   itens seguintes); "As PETs emitidas devem ser rastreáveis." continua sendo item.
7. **IDs repetidos esvaziavam o índice.** A NR-12 repete números de item entre texto e anexo; o
   lote inteiro era recusado e o índice ficava vazio. Hoje os IDs são conferidos **antes** de
   apagar o índice que funciona.
8. **A calibração media outra coisa.** A 1ª versão olhava a nota do 1º trecho depois de ordenar
   por vigência; a resposta decide pela maior nota. Agora as duas usam a mesma função.
9. **O critério de calibração protegia respostas erradas.** "Nunca recusar pergunta do
   gabarito" escolheu 0,002 — a nota de uma pergunta cujo trecho certo nem estava entre os
   candidatos — e deixava passar 8 de 20 perguntas fora do assunto. Recusar o que sairia errado
   não é erro.
10. **A citação vinha de uma remissão ou do anexo errado.** Uma frase quebrada no PDF
    ("…conforme o item / 12.4.7 e seus subitens, desta NR") abria o item 12.4.7 no meio do
    texto de outro item, e o texto dos anexos da NR-12 saía como "item 12.4.3" do texto
    principal. Remissão não abre item, e o anexo leva o rótulo dele ("Anexo X, item 1.3"). Achado
    por uma revisão externa do código, não pela avaliação: o gabarito tem só 5 perguntas da NR-12.

## Limitações (medidas, não escondidas)

- **6 das 40 perguntas não trazem o trecho certo nem entre os 5 primeiros, em nenhum dos
  caminhos medidos** (o cross-encoder só reordena o que a busca entrega): "aliança e relógio" (10.2.9.3, "adornos
  pessoais"), terceirização (10.13.1), desconto do treinamento (12.16.3), corredor pintado
  (12.2.1), "entrar num tanque rapidinho" (33.5.5) e "cinto e linha de vida" (35.5.1). Teto da
  recuperação, não da ordenação — o próximo passo seria um modelo de embeddings maior.
- Com o limiar 0,15 o sistema **recusa 6** das 40 perguntas do gabarito — **5** delas seriam
  respondidas errado; **1** seria respondida certo. Sobram respostas erradas: o 1º trecho
  mostrado não é o item do gabarito em 8 das 34 respondidas.
- O limiar, os 15 candidatos e o reranqueador foram escolhidos olhando o mesmo gabarito; só a
  recusa tem conjunto de teste separado. Os números de acerto são, portanto, otimistas.
- **Lento nesta máquina:** 15 a 30 s por pergunta (cross-encoder de 568 M parâmetros em CPU de
  notebook, ~1 s por trecho; 15 candidatos). Abaixo de 15 candidatos a recuperação cai
  (30/32/34 acertos nos 5/10/15 primeiros; satura em 15).
- **Precisa de ~4 GB de RAM livres** para o cross-encoder. Com 3,7 GB o processo morreu dentro
  do carregamento, sem exceção Python; por isso a checagem vem antes e a API responde 503 com
  a mensagem, em vez de cair. (bfloat16 cabe em metade, mas sem suporte nativo na CPU levou
  15 s por par.)
- O gabarito tem **40 perguntas escritas por uma pessoa**; o lado "dentro do assunto" do limiar
  é a mesma amostra da avaliação. Só as 20 perguntas fora do assunto de teste estão fora dela.
  O número de verdade vem de perguntas reais — o `/painel` existe para colher essas.
- O **manual da NR-35 é de abril de 2018** e a NR-35 foi alterada depois: toda resposta que o
  cita leva aviso.
- A geração com LLM (`ANTHROPIC_API_KEY`) **não foi testada** — só a recuperação está medida.
  Sem a chave, a resposta é o próprio trecho citado.

---

## Como funciona

```
PDF oficial ─► corte POR ITEM da norma ─► embeddings e5 ─► ChromaDB (busca exata na prática)
               · glossário por termo
               · tira cabeçalho/rodapé repetido
               · título vira contexto, não trecho
               · marca revogado

pergunta ─► 15 candidatos (embeddings) ─► cross-encoder (nota 0–1) ─► maior nota < 0,15? ─► "não encontrei"
                                                                    └─► ordena: relevante > vale hoje > nota
                                                                        └─► resposta citada + avisos de data
```

Cortar **por item**, e não por número de caracteres, é o que permite citar o item exato.
Quem pergunta pode restringir a uma norma (`/perguntar?q=...&norma=NR-33`, seletor na tela).

**Registro de uso em SQL.** Toda consulta vai para SQLite (`rag/registro.py`: tabelas
`consulta` e `fonte`, 1:N, chave estrangeira, índices). `GET /painel` devolve, em SQL: taxa de
recusa, itens mais citados, uso por norma, perguntas **recusadas** e as respondidas **perto do
limiar** — as duas últimas são a fila do próximo gabarito.

**Docker e CI.** `Dockerfile` (Python 3.12 slim, torch CPU, usuário sem privilégio, healthcheck,
os dois modelos baixados no build) e `docker-entrypoint.sh` (corta e indexa na 1ª subida a partir
dos PDFs montados em volume). O GitHub Actions roda os testes que não dependem de modelo nem de
corpus **e constrói a imagem**, sobe o container e confere `/saude`.

## Rodar

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# baixe os PDFs listados em data/catalogo.json do gov.br para data/raw/
.venv\Scripts\python -m rag.ingest                    # corta os PDFs
.venv\Scripts\python -c "from rag import busca; busca.indexa(busca.carrega_trechos())"
.venv\Scripts\python -m pytest -q                     # 20 testes (3 usam os modelos)
.venv\Scripts\python -m eval.calibra                  # mede e escolhe o limiar (lento)
.venv\Scripts\python -m eval.avaliar                  # gera eval/RESULTADO.md (lento)
.venv\Scripts\python -m uvicorn api:app --port 8010   # tela em /, /perguntar, /painel, /normas
```

Com Docker:

```bash
docker build -t rag-normas .
docker run -p 8010:8010 -v "$PWD/data/raw:/app/data/raw:ro" rag-normas
```

## Fontes

Textos oficiais do Ministério do Trabalho e Emprego (gov.br), com a vigência de cada um em
[`data/catalogo.json`](data/catalogo.json): NR-10 (2019, vigente), NR-10 (Portaria MTE nº
737/2026, vale a partir de 01/06/2027), NR-12, NR-33 e o manual comentado da NR-35 (2018).
Nem os PDFs nem os trechos extraídos estão no repositório — o manual da NR-35 é obra, não ato
oficial.

---

Rafael Blachi · Caçapava/SP
