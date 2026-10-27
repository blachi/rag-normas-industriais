"""API HTTP + tela do assistente de normas.

    .venv\\Scripts\\python.exe -m uvicorn api:app --port 8010
    abrir http://127.0.0.1:8010            (tela)
    GET   http://127.0.0.1:8010/perguntar?q=quem pode assinar o prontuario eletrico
"""
import logging
import time
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from rag import busca, registro
from rag.rerank import MemoriaInsuficiente
from rag.responder import _catalogo, responde

log = logging.getLogger("rag.api")

app = FastAPI(title="Assistente de Normas Regulamentadoras", version="0.3")


@app.get("/normas")
def normas():
    """As normas que podem ser escolhidas (familias do catalogo: NR-10 reune as duas redacoes)."""
    return sorted({busca.familia(m["norma"]) for m in _catalogo().values()})


@app.get("/perguntar")
def perguntar(q: str = Query(..., min_length=3, max_length=500),
              norma: str | None = Query(None, description="restringe a uma norma, ex.: NR-33")):
    if norma and norma not in normas():
        raise HTTPException(422, f"norma desconhecida: {norma}; use uma de {normas()}")
    t0 = time.perf_counter()
    try:
        r = responde(q, familia=norma)
    except MemoriaInsuficiente as e:   # erro claro em vez de processo morto (ver rag/rerank.py)
        raise HTTPException(503, str(e))
    ms = 1000 * (time.perf_counter() - t0)
    try:
        registro.registra(r, ms, norma)
    except Exception as e:          # registro nunca derruba a resposta; mas avisa no log
        log.warning("registro da consulta falhou: %s", e)
    return asdict(r)


@app.get("/painel")
def painel():
    """Uso real, em SQL: recusas, itens mais citados, perguntas no limite do limiar."""
    return registro.painel()


@app.get("/saude")
def saude():
    return {"ok": True}


TELA = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Assistente de Normas</title>
<style>
:root{--bg:#f6f7f5;--fg:#1d2420;--mut:#5d6862;--card:#fff;--line:#dfe3df;--ac:#1f6f5c;--warn:#8a5a00;--warnbg:#fff6e0;--no:#8f2d2d}
@media (prefers-color-scheme:dark){:root{--bg:#141816;--fg:#e8ece9;--mut:#9aa6a0;--card:#1c211e;--line:#2c332f;--ac:#5cc2a6;--warn:#f0c46a;--warnbg:#2c2614;--no:#e08b8b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:760px;margin:0 auto;padding:32px max(16px,env(safe-area-inset-left)) 64px}
h1{font-size:1.4rem;margin:0 0 4px}p.sub{color:var(--mut);margin:0 0 20px}
form{display:flex;gap:8px;flex-wrap:wrap}select{padding:12px 10px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg);font:inherit}input{flex:1;min-width:12rem;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg);font:inherit}
button{padding:12px 18px;border:0;border-radius:10px;background:var(--ac);color:#fff;font:inherit;cursor:pointer}
.ex{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 24px}.ex span{font-size:.85rem;border:1px solid var(--line);border-radius:99px;padding:4px 10px;cursor:pointer;color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:12px}
.cit{font-size:.85rem;color:var(--ac);font-weight:600;margin-bottom:6px}.sim{float:right;color:var(--mut);font-weight:400}
.aviso{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:10px 14px;margin-bottom:10px;font-size:.92rem}
.nao{color:var(--no)}.mut{color:var(--mut);font-size:.85rem}
</style></head><body><main>
<h1>Assistente de Normas Regulamentadoras</h1>
<p class="sub">Pergunte do jeito que falaria no chão de fábrica. A resposta vem com a norma e o item.</p>
<form id="f"><select id="n" aria-label="Norma"><option value="">Todas as normas</option></select><input id="q" placeholder="Ex.: posso usar aliança mexendo no painel?" autocomplete="off"><button>Perguntar</button></form>
<div class="ex" id="ex"></div><div id="out"></div>
<script>
const EX=["Posso trabalhar no painel usando aliança e relógio?","De quanto em quanto tempo refaço a reciclagem?","Eletricista pode trabalhar sozinho em alta tensão?","Quem pode assinar os documentos técnicos do prontuário elétrico?","Qual a receita de bolo de cenoura?"];
const ex=document.getElementById('ex');EX.forEach(t=>{const s=document.createElement('span');s.textContent=t;s.onclick=()=>{q.value=t;go()};ex.appendChild(s)});
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
fetch('/normas').then(r=>r.json()).then(L=>L.forEach(x=>{const o=document.createElement('option');o.value=o.textContent=x;n.appendChild(o)}));
let seq=0;  // a resposta de uma pergunta antiga, chegando depois, nao pode cobrir a da nova
async function go(){const v=q.value.trim();if(!v)return;const eu=++seq;out.innerHTML='<p class="mut">Buscando… (15 a 30 s)</p>';
let r;try{const u='/perguntar?q='+encodeURIComponent(v)+(n.value?'&norma='+encodeURIComponent(n.value):'');
const resp=await fetch(u);if(!resp.ok)throw new Error('HTTP '+resp.status+(resp.status===503?' — pouca memória livre':''));r=await resp.json()}
catch(e){if(eu===seq)out.innerHTML='<div class="card nao">Falhou ao consultar o servidor ('+esc(e.message)+').</div>';return}
if(eu!==seq)return;
if(!r.encontrou){out.innerHTML='<div class="card nao">'+esc(r.texto)+'</div>';return}
let h=r.avisos.map(a=>'<div class="aviso">⚠ '+esc(a)+'</div>').join('');
h+=r.fontes.map((f,i)=>'<div class="card"><div class="cit">'+(i?'':'Resposta · ')+esc(f.norma)+' — item '+esc(f.item)+' · p. '+f.pagina+'<span class="sim">relevância '+f.relevancia.toFixed(2)+'</span></div>'+esc(f.texto)+'</div>').join('');
out.innerHTML=h}
document.getElementById('f').onsubmit=e=>{e.preventDefault();go()};
</script></main></body></html>"""


@app.get("/", response_class=HTMLResponse)
def tela():
    return TELA
