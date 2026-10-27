# Resultado da avaliação — 40 perguntas, top-5

| Buscador | acerto@1 | acerto@5 | MRR | ms/pergunta | aviso de revogado |
|---|---|---|---|---|---|
| bm25 | 15% | 48% | 0.260 | 1.9 | 0/2 |
| semantica | 40% | 75% | 0.541 | 343.9 | 1/2 |
| hibrida | 28% | 68% | 0.420 | 42.4 | 1/2 |
| semantica+vigencia | 52% | 78% | 0.617 | 40.4 | 0/2 |
| com norma escolhida | 55% | 78% | 0.642 | 57.4 | 0/2 |
| reranqueada | 70% | 82% | 0.751 | 16710.0 | 1/2 |
| reranqueada + norma escolhida | 70% | 85% | 0.760 | 15889.4 | 1/2 |

## Por norma (reranqueada, o caminho em uso)

| Norma | perguntas | acerto@1 | acerto@5 |
|---|---|---|---|
| NR-10 | 25 | 20/25 | 22/25 |
| NR-12 | 5 | 2/5 | 3/5 |
| NR-33 | 5 | 3/5 | 4/5 |
| NR-35 (manual) | 5 | 3/5 | 4/5 |

## Onde o caminho em uso (reranqueada) errou

Posição do item certo (— = fora dos 5) e os 3 primeiros trazidos. `*` = trecho de outra redação/norma que não a do gabarito.

| Pergunta | Certo | bm25 | semantica | hibrida | semantica+vigencia | com norma escolhida | reranqueada | reranqueada + norma escolhida |
|---|---|---|---|---|---|---|---|---|
| Posso trabalhar no painel elétrico usando aliança e relógio? | 10.2.9.3 | — (10.8.6, Anexo I*, 35.4.1.1*) | — (Anexo III*, Anexo III*, 10.8.4*) | — (10.8.4*, 10.8.6, Anexo III*) | — (12.4.3*, 33.3.4.1.1*, 35.4.5.1*) | — (10.5.3, Anexo III*, Anexo III*) | — (10.5.3, 12.4.3*, 35.4.5.1*) | — (10.5.3, 10.12.5*, 10.7.7.1*) |
| Qual é a primeira medida de proteção coletiva que deve ser adotada? | 10.2.8.2 | 5 (12.4.13.1.1*, 10.6.1.1*, 12.5.13*) | — (10.6.8*, 10.6.7*, 10.6.1.2*) | — (10.6.8*, 10.6.1.1*, 10.6.7*) | 5 (10.2.8.1, 12.1.8*, 10.2.9.1) | 4 (10.2.8.1, 10.2.9.1, 10.2.8.2.1) | — (35.4.2*, 10.2.8.2.1, 10.2.8.1) | 4 (10.2.8.2.1, 10.2.8.1, 10.2.9.1) |
| O trabalhador pode se recusar a fazer o serviço se achar que corre risco grave? | 10.14.1 | — (Glossário: Direito de Recusa, 10.16.1*, Glossário: Condições impeditivas*) | 1 (10.14.1, 35.2.2*, Glossário: Direito de Recusa) | 5 (Glossário: Direito de Recusa, 10.16.1*, 35.2.2*) | — (35.2.2*, Glossário: Direito de Recusa, 10.13.4) | — (Glossário: Direito de Recusa, 10.13.4, 10.12.2) | 5 (Glossário: Direito de Recusa, 35.2.2*, 35.3.2*) | 3 (Glossário: Direito de Recusa, 10.13.4, 10.14.1) |
| Se a empresa terceiriza o serviço elétrico, de quem é a responsabilidade pela segurança? | 10.13.1 | — (10.4.8.1*, 10.4.8*, 10.13.4) | — (10.13.3, 10.14.2*, 33.3.2*) | — (10.4.8*, 10.4.8.1*, 10.13.4) | — (10.13.3, 33.3.2*, 10.5.4) | — (10.13.3, 10.5.4, 10.12.1) | — (10.13.2, 10.6.5, 10.13.4) | — (10.13.2, 10.6.5, 10.13.4) |
| Os eletricistas precisam saber fazer resgate e primeiros socorros? | 10.12.2 | 2 (Glossário: Plano de resgate*, 10.12.2, 35.6.4*) | 1 (10.12.2, 35.6.4*, 10.6.3) | 1 (10.12.2, 35.6.4*, Anexo III*) | 1 (10.12.2, 35.6.4*, 10.6.3) | 1 (10.12.2, 10.6.3, 10.6.1.1) | 2 (35.6.4*, 10.12.2, 35.3.2*) | 1 (10.12.2, 10.12.4, 10.8.8) |
| Toda máquina precisa ter botão de emergência? | 12.6.1 | — (12.6.7.1, 10.11.6*, Anexo VII) | 1 (12.6.1, 12.5.1.1, 12.5.1.1) | — (12.5.1.1, 12.5.1.1, 12.5.1.1) | 1 (12.6.1, 12.5.1.1, 12.5.1.1) | 1 (12.6.1, 12.5.1.1, 12.5.1.1) | 2 (Anexo IX, 12.6.1, 12.5.1.1) | 2 (Anexo IX, 12.6.1, 12.5.1.1) |
| O treinamento do operador pode ser descontado do salário dele? | 12.16.3 | — (12.5.1.1, 35.3.3*, Anexo V) | — (35.3.3.1*, 35.3.3*, 35.3.3*) | — (35.3.3*, 10.9.5*, 35.3.3*) | — (35.3.3.1*, 35.3.3*, 35.3.3*) | — (12.1.10, Anexo V, 12.16.6.1) | — (35.3.3*, 35.3.6*, 35.3.7*) | — (Anexo V, 12.16.6.1, 12.1.10) |
| O corredor em volta das máquinas precisa ser pintado no chão? | 12.2.1 | — (35.5.9.1*, 35.5.11*, Glossário: Trava-quedas*) | — (12.1, 12.15.1.1, 12.5.1.1) | — (12.1.4, 35.5.9.1*, 12.1) | — (12.1, 12.15.1.1, 12.5.1.1) | — (12.1, 12.15.1.1, 12.5.1.1) | — (12.7.8.1, 12.4.3, Anexo IX) | — (12.7.8.1, Anexo X, 12.4.3) |
| Por quanto tempo tenho que guardar a permissão de entrada em espaço confinado? | 33.5.9 | — (33.7.1, 33.4.2, 33.5.16.1) | — (33.7.1, 33.5.16.1, 33.5.5) | — (33.7.1, 33.5.16.1, 33.5.6) | — (33.7.1, 33.5.16.1, 33.5.5) | — (33.7.1, 33.5.16.1, 33.5.5) | 2 (33.5.12.1.1, 33.5.9, 33.5.12) | 2 (33.5.12.1.1, 33.5.9, 33.5.12) |
| Posso entrar num tanque sem permissão escrita se for rapidinho? | 33.5.5 | — (Anexo II, Glossário: Etiquetagem, Glossário: Colhedora de grãos*) | — (35.4.7*, Anexo XII*, 12.12.4.1*) | — (Anexo II, 35.4.7*, 35.4.8*) | — (35.4.7*, Anexo XII*, 12.12.4.1*) | — (Anexo II, 33.5.16.3, 33.6.4) | — (Anexo II, Anexo XII*, 35.4.7*) | — (33.7.1, Anexo II, 33.5.16.1) |
| Quando é obrigatório usar cinto e linha de vida? | 35.5.1 | — (33.5.17.2*, Anexo II, Glossário: Trava-quedas) | — (Referências, Glossário: Vida útil de máquina e equipamento*, 12.8.6.2*) | — (Referências, Anexo II, Glossário: Vida útil de máquina e equipamento*) | — (Referências, Glossário: Vida útil de máquina e equipamento*, 12.8.6.2*) | — (Referências, Glossário: Cinturão de segurança tipo paraquedista, 35.4.2) | — (Anexo II*, 35.4.2, Referências) | — (35.4.2, Referências, Anexo II) |
| A empresa precisa ter equipe de resgate para trabalho em altura? | 35.6.1 | 5 (35.6.1.1, 35.3.2, 35.6.4) | 1 (35.6.1, 35.6.4, 35.6.1.1) | 3 (35.6.1.1, 35.6.4, 35.6.1) | 1 (35.6.1, 35.6.4, 35.6.1.1) | 1 (35.6.1, 35.6.4, 35.6.1.1) | 3 (35.6.1.1, 35.6.4, 35.6.1) | 3 (35.6.1.1, 35.6.4, 35.6.1) |

## Recusa — testada em 20 perguntas fora do assunto que NÃO entraram na calibração

Limiar em uso: **0.15** sobre a relevância do cross-encoder (escolhido em `eval/calibra.py`).

**Como era: similaridade do embedding** — gabarito: mínima 0.843 · fora do assunto: máxima 0.856

| Limiar | Pergunta boa recusada | Fora do assunto aceita |
|---|---|---|
| 0.82 | 0/40 | 18/20 |
| 0.835 | 0/40 | 9/20 |
| 0.85 | 3/40 | 1/20 |
| 0.86 | 6/40 | 0/20 |

**Como é: relevância do cross-encoder** — gabarito: mínima 0.002 · fora do assunto: máxima 0.055

| Limiar | Pergunta boa recusada | Fora do assunto aceita |
|---|---|---|
| 0.01 | 3/40 | 3/20 |
| 0.05 | 5/40 | 1/20 |
| 0.1 | 5/40 | 0/20 |
| 0.15 | 6/40 | 0/20 |
| 0.3 | 10/40 | 0/20 |
| 0.5 | 12/40 | 0/20 |
