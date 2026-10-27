#!/bin/sh
# Corta e indexa na 1a subida (ou quando nao ha indice); depois so sobe a API.
set -e
if [ ! -s data/trechos.jsonl ] || [ ! -d data/chroma ]; then
  if ls data/raw/*.pdf >/dev/null 2>&1; then
    python -m rag.ingest
    python -c "from rag import busca; print('indexados', busca.indexa(busca.carrega_trechos()))"
  else
    echo "AVISO: sem PDFs em /app/data/raw — a API sobe, mas sem indice (toda pergunta sera recusada)." >&2
  fi
fi
exec python -m uvicorn api:app --host 0.0.0.0 --port 8010
