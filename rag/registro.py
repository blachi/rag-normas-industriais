"""Registro de consultas em SQLite e o painel que sai dele em SQL.

Para que serve, alem de "ter banco": as perguntas que o sistema RECUSA ou responde com
relevancia baixa sao exatamente as que faltam no gabarito. O painel e a fila de
trabalho da proxima rodada de avaliacao.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

BANCO = Path(__file__).resolve().parent.parent / "data" / "consultas.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS consulta (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    quando        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')),
    pergunta      TEXT    NOT NULL,
    norma_escolhida TEXT,               -- NULL = todas as normas
    encontrou     INTEGER NOT NULL CHECK (encontrou IN (0, 1)),
    relevancia    REAL,                 -- nota do cross-encoder do 1o trecho (tambem quando recusa)
    ms            REAL    NOT NULL,
    n_avisos      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS fonte (      -- 1:N: cada resposta cita varios trechos, em ordem
    consulta_id   INTEGER NOT NULL REFERENCES consulta(id) ON DELETE CASCADE,
    posicao       INTEGER NOT NULL,
    norma         TEXT    NOT NULL,
    item          TEXT    NOT NULL,
    relevancia    REAL    NOT NULL,
    PRIMARY KEY (consulta_id, posicao)
);
CREATE INDEX IF NOT EXISTS ix_consulta_quando ON consulta(quando);
CREATE INDEX IF NOT EXISTS ix_fonte_item ON fonte(norma, item);
"""

PAINEL = {
    "resumo": """
        SELECT COUNT(*)                                   AS consultas,
               ROUND(100.0 * AVG(1 - encontrou), 1)       AS pct_recusa,
               ROUND(AVG(ms), 0)                          AS ms_medio,
               ROUND(AVG(CASE WHEN encontrou THEN relevancia END), 3) AS relevancia_media_respondidas
        FROM consulta""",
    "itens_mais_citados": """
        SELECT f.norma, f.item, COUNT(*) AS vezes_em_1o
        FROM fonte f JOIN consulta c ON c.id = f.consulta_id
        WHERE f.posicao = 1 AND c.encontrou = 1
        GROUP BY f.norma, f.item
        ORDER BY vezes_em_1o DESC, f.norma, f.item
        LIMIT 10""",
    "recusadas_recentes": """
        SELECT quando, pergunta, ROUND(relevancia, 3) AS relevancia
        FROM consulta WHERE encontrou = 0
        ORDER BY id DESC LIMIT 10""",
    "respondidas_no_limite": """
        -- respondeu, mas perto do limiar: candidatas a entrar no gabarito
        SELECT quando, pergunta, ROUND(relevancia, 3) AS relevancia
        FROM consulta WHERE encontrou = 1
        ORDER BY relevancia ASC LIMIT 10""",
    "por_norma_escolhida": """
        SELECT COALESCE(norma_escolhida, 'todas') AS norma, COUNT(*) AS consultas,
               ROUND(100.0 * AVG(1 - encontrou), 1) AS pct_recusa
        FROM consulta GROUP BY norma ORDER BY consultas DESC""",
    "por_dia": """
        SELECT substr(quando, 1, 10) AS dia, COUNT(*) AS consultas, SUM(1 - encontrou) AS recusadas
        FROM consulta GROUP BY dia ORDER BY dia DESC LIMIT 30""",
}


def _conecta(banco: Path) -> sqlite3.Connection:
    banco.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(banco)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


def registra(resposta, ms: float, norma_escolhida: str | None = None, banco: Path = BANCO) -> int:
    with closing(_conecta(banco)) as con, con:
        cur = con.execute(
            "INSERT INTO consulta (pergunta, norma_escolhida, encontrou, relevancia, ms, n_avisos) VALUES (?, ?, ?, ?, ?, ?)",
            (resposta.pergunta, norma_escolhida, int(resposta.encontrou), resposta.relevancia_topo, ms, len(resposta.avisos)),
        )
        cid = cur.lastrowid
        con.executemany(
            "INSERT INTO fonte (consulta_id, posicao, norma, item, relevancia) VALUES (?, ?, ?, ?, ?)",
            [(cid, i, f["norma"], f["item"], f["relevancia"]) for i, f in enumerate(resposta.fontes, start=1)],
        )
        return cid


def painel(banco: Path = BANCO) -> dict:
    with closing(_conecta(banco)) as con:
        con.row_factory = sqlite3.Row
        return {nome: [dict(r) for r in con.execute(sql)] for nome, sql in PAINEL.items()}
