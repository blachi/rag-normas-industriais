# Resultado da avaliação — 40 perguntas, top-5

| Buscador | acerto@1 | acerto@5 | MRR | ms/pergunta | aviso de revogado |
|---|---|---|---|---|---|
| bm25 | 12% | 45% | 0.236 | 3.5 | 0/2 |
| semantica | 38% | 70% | 0.506 | 557.6 | 1/2 |
| hibrida | 22% | 65% | 0.375 | 72.4 | 1/2 |
| semantica+vigencia | 50% | 75% | 0.586 | 62.7 | 0/2 |
| com norma escolhida | 52% | 75% | 0.615 | 90.4 | 0/2 |
| reranqueada | 68% | 82% | 0.736 | 16095.7 | 1/2 |
| reranqueada + norma escolhida | 68% | 85% | 0.746 | 14731.5 | 1/2 |

## Por norma (reranqueada, o caminho em uso)

| Norma | perguntas | acerto@1 | acerto@5 |
|---|---|---|---|
| NR-10 | 25 | 20/25 | 22/25 |
| NR-12 | 5 | 2/5 | 3/5 |
| NR-33 | 5 | 3/5 | 4/5 |
| NR-35 (manual) | 5 | 2/5 | 4/5 |

## Onde o caminho em uso (reranqueada) errou

Posição do item certo (— = fora dos 5) e os 3 primeiros trazidos. `*` = trecho de outra redação/norma que não a do gabarito.

| Pergunta | Certo | bm25 | semantica | hibrida | semantica+vigencia | com norma escolhida | reranqueada | reranqueada + norma escolhida |
|---|---|---|---|---|---|---|---|---|
| Posso trabalhar no painel elétrico usando aliança e relógio? | 10.2.9.3 | — (Anexo VIII, item 2.7.2*, 10.8.6, Anexo IX, item 1.2.4.3.1*) | — (10.8.4*, Anexo III, item 9.3*, Anexo III, item 9.3*) | — (Anexo VIII, item 2.7.2*, 10.8.4*, 10.8.6) | — (33.3.4.1.1*, 35.4.5.1*, 10.5.3) | — (10.5.3, 10.8.4*, Anexo III, item 9.3*) | — (10.5.3, 35.4.5.1*, 33.3.4.1.1*) | — (10.5.3, 10.12.5*, 10.7.7.1*) |
| Qual é a primeira medida de proteção coletiva que deve ser adotada? | 10.2.8.2 | 5 (10.6.1.1*, 12.4.13.1.1*, 12.5.13*) | — (10.6.8*, 10.6.7*, 10.6.1.2*) | — (10.6.8*, 10.6.1.1*, 10.6.7*) | 5 (10.2.8.1, 12.1.8*, 10.2.9.1) | 4 (10.2.8.1, 10.2.9.1, 10.2.8.2.1) | — (35.4.2*, 10.2.8.2.1, 10.2.8.1) | 4 (10.2.8.2.1, 10.2.8.1, 10.2.9.1) |
| O trabalhador pode se recusar a fazer o serviço se achar que corre risco grave? | 10.14.1 | — (Glossário: Direito de Recusa, 10.16.1*, Glossário: Condições impeditivas*) | 1 (10.14.1, 35.2.2*, Glossário: Direito de Recusa) | 5 (Glossário: Direito de Recusa, 10.16.1*, 35.3.2*) | — (35.2.2*, Glossário: Direito de Recusa, 10.13.4) | — (Glossário: Direito de Recusa, 10.13.4, 10.12.2) | 5 (Glossário: Direito de Recusa, 35.2.2*, 35.3.2*) | 3 (Glossário: Direito de Recusa, 10.13.4, 10.14.1) |
| Se a empresa terceiriza o serviço elétrico, de quem é a responsabilidade pela segurança? | 10.13.1 | — (10.4.8.1*, 10.4.8*, 10.13.4) | — (10.13.3, 10.14.2*, 33.3.2*) | — (10.4.8*, 10.4.8.1*, 10.13.4) | — (10.13.3, 33.3.2*, 10.5.4) | — (10.13.3, 10.5.4, 10.12.1) | — (10.13.2, 10.6.5, 10.13.4) | — (10.13.2, 10.6.5, 10.13.4) |
| Os eletricistas precisam saber fazer resgate e primeiros socorros? | 10.12.2 | 2 (Glossário: Plano de resgate*, 10.12.2, 33.3.6*) | 1 (10.12.2, 35.6.4*, 10.6.3) | 1 (10.12.2, 35.6.4*, 35.3.2*) | 1 (10.12.2, 35.6.4*, 10.6.3) | 1 (10.12.2, 10.6.3, 10.6.1.1) | 2 (35.6.4*, 10.12.2, 35.3.2*) | 1 (10.12.2, 10.12.4, 10.8.8) |
| Toda máquina precisa ter botão de emergência? | 12.6.1 | — (Anexo VIII, item 2.7.2, 12.6.7.1, Anexo VI, item 3.7) | — (Anexo VI, item 6.3, Anexo IX, item 1.2.6.3.4, Anexo IX, item 1.2.6.3.5) | — (Anexo VI, item 6.3, Anexo VIII, item 2.7.2, Anexo VI, item 3.7) | — (Anexo VI, item 6.3, Anexo IX, item 1.2.6.3.4, Anexo IX, item 1.2.6.3.5) | — (Anexo VI, item 6.3, Anexo IX, item 1.2.6.3.4, Anexo IX, item 1.2.6.3.5) | 2 (Anexo VIII, item 2.7.2, 12.6.1, Anexo VI, item 8.3) | 2 (Anexo VIII, item 2.7.2, 12.6.1, Anexo VI, item 8.3) |
| O treinamento do operador pode ser descontado do salário dele? | 12.16.3 | — (Anexo XI, item 6.11, 12.5.1.1, 35.3.3*) | — (35.3.3.1*, 35.3.3*, 35.3.3*) | — (35.3.3*, 35.3.3*, 10.9.5*) | — (35.3.3.1*, 35.3.3*, 35.3.3*) | — (Anexo V, item 4.1, 12.1.10, 12.16.6.1) | — (Anexo V, item 4.1, 35.3.3*, 35.3.6*) | — (Anexo V, item 4.1, 12.16.6.1, 12.1.10) |
| O corredor em volta das máquinas precisa ser pintado no chão? | 12.2.1 | — (35.5.9.1*, Glossário: Normas do tipo C, Anexo VIII, item 1.2.1) | — (Anexo X, item 13.1, Anexo X, item 30.1, Anexo X, item 1.1) | — (Anexo IX, item 1.2.7.1, 12.1.4, 35.5.9.1*) | — (Anexo X, item 13.1, Anexo X, item 30.1, Anexo X, item 1.1) | — (Anexo X, item 13.1, Anexo X, item 30.1, Anexo X, item 1.1) | — (Anexo X, item 1.1, Anexo IX, item 1.2.8.2, Anexo X, item 31.3) | — (Anexo X, item 1.1, Anexo IX, item 1.2.8.2, Anexo X, item 31.3) |
| Por quanto tempo tenho que guardar a permissão de entrada em espaço confinado? | 33.5.9 | — (33.7.1, 33.4.2, 33.5.16.1) | — (33.7.1, 33.5.16.1, 33.5.5) | — (33.7.1, 33.5.16.1, 33.5.5) | — (33.7.1, 33.5.16.1, 33.5.5) | — (33.7.1, 33.5.16.1, 33.5.5) | 2 (33.5.12.1.1, 33.5.9, 33.5.12) | 2 (33.5.12.1.1, 33.5.9, 33.5.12) |
| Posso entrar num tanque sem permissão escrita se for rapidinho? | 33.5.5 | — (Anexo II, Anexo XI, item 15.25*, 35.4.8*) | — (35.4.7*, 12.12.4.1*, Anexo II) | — (Anexo II, 35.4.7*, 10.7.2.3*) | — (35.4.7*, 12.12.4.1*, Anexo II) | — (Anexo II, 33.5.16.3, 33.6.4) | — (Anexo II, Anexo XII, item 7.3*, 35.4.7*) | — (33.7.1, Anexo II, 33.5.16.1) |
| Preciso fazer análise de risco antes de subir no telhado? | 35.4.5 | 2 (35.5.6.1, 35.4.5, Glossário: Avaliação de Risco*) | 5 (Anexo I, item 1.2, 35.5.11, Anexo XII, item 4.11*) | — (Anexo I, item 1.2, 35.5.8.1, Glossário: Análise de risco*) | 5 (Anexo I, item 1.2, 35.5.11, Anexo XII, item 4.11*) | 4 (Anexo I, item 1.2, 35.5.11, 35.4.5.1) | 2 (Anexo I, item 1.2, 35.4.5, 35.5.8.1) | 2 (Anexo I, item 1.2, 35.4.5, 35.5.8.1) |
| Quando é obrigatório usar cinto e linha de vida? | 35.5.1 | — (Anexo II, item 4.1.1, 33.5.17.2*, Glossário: Trava-quedas) | — (Referências, Glossário: Vida útil de máquina e equipamento*, Anexo II) | — (Referências, Anexo I, item 3.3, 35.5.11) | — (Referências, Glossário: Vida útil de máquina e equipamento*, Anexo II) | — (Referências, Anexo II, Anexo I, item 3.4.1) | — (Anexo II, 35.4.2, Anexo XII, item 4.28*) | — (Anexo II, 35.4.2, Referências) |
| A empresa precisa ter equipe de resgate para trabalho em altura? | 35.6.1 | 5 (Anexo I, item 4.1, 35.6.1.1, 35.3.2) | 1 (35.6.1, 35.6.4, 35.6.1.1) | 3 (Anexo I, item 4.1, 35.6.1.1, 35.6.1) | 1 (35.6.1, 35.6.4, 35.6.1.1) | 1 (35.6.1, 35.6.4, 35.6.1.1) | 4 (35.6.1.1, 35.6.4, Anexo I, item 4.1) | 4 (35.6.1.1, 35.6.4, Anexo I, item 4.1) |

## Recusa — testada em 20 perguntas fora do assunto que NÃO entraram na calibração

Limiar em uso: **0.15** sobre a relevância do cross-encoder (escolhido em `eval/calibra.py`).

**Como era: similaridade do embedding** — gabarito: mínima 0.843 · fora do assunto: máxima 0.856

| Limiar | Pergunta boa recusada | Fora do assunto aceita |
|---|---|---|
| 0.82 | 0/40 | 19/20 |
| 0.835 | 0/40 | 11/20 |
| 0.85 | 2/40 | 1/20 |
| 0.86 | 6/40 | 0/20 |

**Como é: relevância do cross-encoder** — gabarito: mínima 0.001 · fora do assunto: máxima 0.055

| Limiar | Pergunta boa recusada | Fora do assunto aceita |
|---|---|---|
| 0.01 | 3/40 | 3/20 |
| 0.05 | 5/40 | 1/20 |
| 0.1 | 5/40 | 0/20 |
| 0.15 | 6/40 | 0/20 |
| 0.3 | 9/40 | 0/20 |
| 0.5 | 12/40 | 0/20 |
