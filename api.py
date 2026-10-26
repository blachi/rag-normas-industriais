"""API HTTP do assistente de normas.

    .venv\\Scripts\\python.exe -m uvicorn api:app --port 8010
    GET http://127.0.0.1:8010/perguntar?q=quem pode assinar o prontuario eletrico
"""
from dataclasses import asdict

from fastapi import FastAPI, Query

from rag.responder import responde

app = FastAPI(title="Assistente de Normas Regulamentadoras", version="0.1")


@app.get("/perguntar")
def perguntar(q: str = Query(..., min_length=3, max_length=500)):
    return asdict(responde(q))


@app.get("/saude")
def saude():
    return {"ok": True}
