"""Testes do que nao pode quebrar sem ninguem ver.

Os de corte (ingest) rodam sem modelo. Os de resposta usam o indice ja construido
(python -m rag.ingest && python -c "from rag import busca; busca.indexa(busca.carrega_trechos())").
"""
import json

import pytest

from rag import busca, ingest


@pytest.fixture(scope="module")
def trechos():
    # os PDFs e os trechos nao vao para o repositorio (manual da NR-35 e obra, nao ato oficial);
    # no CI estes testes pulam e rodam so os que nao dependem do corpus
    if not busca.TRECHOS.exists():
        pytest.skip("sem corpus: rode python -m rag.ingest com os PDFs em data/raw")
    return busca.carrega_trechos()


def test_todo_trecho_tem_item_e_pagina(trechos):
    assert trechos, "rode python -m rag.ingest antes"
    for t in trechos:
        assert t["item"] and t["pagina"] >= 1 and t["texto"].strip()


def test_ids_unicos(trechos):
    # 26/10: a NR-12 repete numero de item entre texto e anexo; ID por item duplicou e o
    # ChromaDB recusou o lote inteiro, deixando o indice VAZIO (semantica 0%)
    ids = [t["id"] for t in trechos]
    assert len(ids) == len(set(ids))


def test_item_nao_mistura_normas(trechos):
    # um trecho da NR-10 nunca pode carregar item 12.x (numero solto no meio do texto)
    for t in trechos:
        if t["item"][0].isdigit():
            assert t["item"].split(".")[0] == t["norma"].split("-")[1].split()[0], t["id"]


def test_glossario_nao_gruda_no_ultimo_item(trechos):
    ultimo = [t for t in trechos if t["item"] == "10.14.6"]
    assert ultimo and all("Alta Tensão (AT)" not in t["texto"] for t in ultimo)
    assert any(t["item"].startswith("Glossário: Alta Tensão") for t in trechos)


def test_item_revogado_e_marcado(trechos):
    t = next(t for t in trechos if t["item"] == "10.13.1")
    assert t["revogado"] is True
    assert not next(t for t in trechos if t["item"] == "10.2.7")["revogado"]


def test_nenhum_trecho_real_passa_do_limite(trechos):
    # a classe do defeito de 26/10: o glossario da NR-12 (formato sem numero) saiu com 47 mil
    # caracteres porque o caminho do glossario nao passava pelo limite. Vale para TODO trecho.
    maior = max(trechos, key=lambda t: len(t["texto"]))
    assert len(maior["texto"]) <= ingest.MAX_CHARS + 200, (maior["norma"], maior["item"], len(maior["texto"]))


def test_glossario_sem_numero_separa_por_termo():
    defs = ingest._definicoes("Barreira: dispositivo que impede o contato. Bloqueio: ação destinada a manter. "
                              "Observação: isto nao e termo. Talabarte: dispositivo de conexão.")
    termos = [t for t, _ in defs]
    assert termos == ["Barreira", "Bloqueio", "Talabarte"]


def test_rodape_repetido_sai():
    rod = "Este texto não substitui o publicado no DOU"
    pags = [(i, f"33.{i} item {i} texto\n{rod}") for i in range(1, 7)]
    limpo = ingest._sem_cabecalho_rodape(pags)
    assert all(rod not in t for _, t in limpo)
    assert all(f"item {n}" in t for n, t in limpo)


def test_quebra_respeita_tamanho():
    longo = "a) " + "texto de alinea; " * 400
    assert all(len(p) <= ingest.MAX_CHARS + 200 for p in ingest._quebra(longo))


def test_bm25_acha_termo_exato(trechos):
    b = busca.BM25(trechos)
    assert b.busca("adornos pessoais", 1)[0][0]["item"] == "10.2.9.3"


def test_ordem_relevante_antes_de_vigente():
    # um trecho vigente IRRELEVANTE nao pode passar na frente de um relevante da redacao nova
    import datetime as dt
    from rag.responder import ordena
    velho_irrelevante = ({"documento": "nr-10-atualizada-2019-1.pdf", "item": "10.1.1"}, 0.02)
    novo_relevante = ({"documento": "portaria-mte-no-737-nova-nr-10.pdf", "item": "10.4.8"}, 0.91)
    velho_relevante = ({"documento": "nr-10-atualizada-2019-1.pdf", "item": "10.13.1"}, 0.60)
    ordem = ordena([velho_irrelevante, novo_relevante, velho_relevante], 0.5, dt.date(2026, 10, 26))
    assert [t["item"] for t, _ in ordem] == ["10.13.1", "10.4.8", "10.1.1"]
    # depois da vigencia da nova redacao, as duas valem e decide a nota
    ordem = ordena([velho_irrelevante, novo_relevante, velho_relevante], 0.5, dt.date(2027, 6, 2))
    assert [t["item"] for t, _ in ordem][0] == "10.4.8"
    # item REVOGADO nao vale hoje: relevante, mas atras de um relevante em vigor
    revogado = ({"documento": "nr-10-atualizada-2019-1.pdf", "item": "10.14.1", "revogado": True}, 0.99)
    vigente = ({"documento": "nr-10-atualizada-2019-1.pdf", "item": "Glossário: Direito de Recusa"}, 0.70)
    ordem = ordena([revogado, vigente], 0.5, dt.date(2026, 10, 26))
    assert [t["item"] for t, _ in ordem] == ["Glossário: Direito de Recusa", "10.14.1"]


def test_titulo_de_secao_nao_vira_trecho(trechos):
    # "12.1 Princípios gerais", "33.5.13 Sinalização de segurança": titulo (contexto), nao trecho
    curtos_sem_verbo = [t for t in trechos if t["item"][0].isdigit() and len(t["texto"]) <= 60
                        and not ingest.VERBO_NORMATIVO.search(t["texto"])]
    assert not curtos_sem_verbo, [(t["norma"], t["item"], t["texto"]) for t in curtos_sem_verbo[:5]]
    # e a obrigacao curta continua sendo trecho
    assert any(t["item"] == "33.5.8" and "rastreáveis" in t["texto"] for t in trechos)


def test_calibracao_nao_protege_resposta_errada():
    # 1a versao: "nunca recusar pergunta do gabarito" escolheu 0,002 e deixou passar 8 de 20
    # perguntas fora do assunto. Recusar o que sairia ERRADO nao e erro.
    from eval import calibra
    doc = "nr-12-atualizada-2022-1.pdf"
    def g(nota, item_topo, item_certo):
        return {"pergunta": item_certo, "itens": [item_certo], "norma": "NR-12", "nota": nota,
                "candidatos": [{"item": item_topo, "norma": "NR-12", "documento": doc, "nota": nota}]}
    gabarito = [g(0.95, "12.6.1", "12.6.1"), g(0.90, "12.13.1", "12.13.1"),
                g(0.004, "12.1.1", "12.2.1")]                          # nota baixa E errada
    fora = [{"pergunta": "bolo", "nota": 0.01}, {"pergunta": "copa", "nota": 0.03}]
    escolhido = calibra.escolhe({"gabarito": gabarito, "calibracao": fora, "teste": fora})
    assert escolhido["erros_na_calibracao"]["total"] == 0
    assert 0.03 < escolhido["limiar"] <= 0.90


def test_aviso_de_vigencia_depende_da_data():
    import datetime as dt
    from rag.responder import _avisos
    velha = {"norma": "NR-10", "item": "10.2.7", "documento": "nr-10-atualizada-2019-1.pdf"}
    nova = {"norma": "NR-10 (2026)", "item": "10.2.7", "documento": "portaria-mte-no-737-nova-nr-10.pdf"}
    antes = dt.date(2026, 10, 26)
    depois = dt.date(2027, 6, 2)
    assert any("só vale a partir de 01/06/2027" in a for a in _avisos([nova], antes))
    assert any("vigente até 31/05/2027" in a for a in _avisos([velha], antes))
    assert not any("só vale a partir" in a for a in _avisos([nova], depois))
    assert any("deixou de valer em 31/05/2027" in a for a in _avisos([velha], depois))


def test_registro_sql_e_painel(tmp_path):
    from rag import registro
    from rag.responder import Resposta
    banco = tmp_path / "c.db"
    ok = Resposta("quem assina o prontuario?", True, "x",
                  fontes=[{"norma": "NR-10", "item": "10.2.7", "relevancia": 0.9}], relevancia_topo=0.9)
    nao = Resposta("receita de bolo", False, "Não encontrei", relevancia_topo=0.10)
    registro.registra(ok, 120.0, None, banco)
    registro.registra(ok, 80.0, "NR-10", banco)
    registro.registra(nao, 50.0, None, banco)
    p = registro.painel(banco)
    assert p["resumo"][0]["consultas"] == 3
    assert p["resumo"][0]["pct_recusa"] == pytest.approx(33.3)
    assert p["itens_mais_citados"][0] == {"norma": "NR-10", "item": "10.2.7", "vezes_em_1o": 2}
    assert p["recusadas_recentes"][0]["pergunta"] == "receita de bolo"
    assert {r["norma"]: r["consultas"] for r in p["por_norma_escolhida"]} == {"todas": 2, "NR-10": 1}


@pytest.mark.modelo
def test_indice_bate_com_busca_exata():
    # o indice aproximado nao pode perder vizinho: compara com cosseno exato em todos os vetores
    import json
    import numpy as np
    col = busca._colecao()
    tudo = col.get(include=["embeddings"])
    E = np.array(tudo["embeddings"])
    perguntas = [json.loads(l)["pergunta"] for l in open(busca.RAIZ / "eval" / "perguntas.jsonl", encoding="utf-8") if l.strip()]
    Q = busca._modelo().encode([f"query: {q}" for q in perguntas], normalize_embeddings=True)
    for q, v in zip(perguntas, Q):
        exato = {tudo["ids"][i] for i in np.argsort(-E @ v)[:5]}
        assert exato == {t["id"] for t, _ in busca.semantica(q, 5)}, q


@pytest.mark.modelo
def test_resposta_cita_item_certo():
    from rag.responder import responde
    r = responde("Quem pode assinar os documentos técnicos do prontuário elétrico?")
    assert r.encontrou and r.fontes[0]["item"] == "10.2.7"


@pytest.mark.modelo
def test_fora_do_assunto_recusa():
    from rag.responder import responde
    r = responde("Qual a receita de bolo de cenoura?")
    assert not r.encontrou and "Não encontrei" in r.texto
