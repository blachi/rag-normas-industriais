"""Testes do que nao pode quebrar sem ninguem ver.

Os de corte (ingest) rodam sem modelo. Os de resposta usam o indice ja construido
(python -m rag.ingest && python -c "from rag import busca; busca.indexa(busca.carrega_trechos())").
"""
import json

import pytest

from rag import busca, ingest


@pytest.fixture(scope="module")
def trechos():
    return busca.carrega_trechos()


def test_todo_trecho_tem_item_e_pagina(trechos):
    assert trechos, "rode python -m rag.ingest antes"
    for t in trechos:
        assert t["item"] and t["pagina"] >= 1 and t["texto"].strip()


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


def test_quebra_respeita_tamanho():
    longo = "a) " + "texto de alinea; " * 400
    assert all(len(p) <= ingest.MAX_CHARS + 200 for p in ingest._quebra(longo))


def test_bm25_acha_termo_exato(trechos):
    b = busca.BM25(trechos)
    assert b.busca("adornos pessoais", 1)[0][0]["item"] == "10.2.9.3"


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
