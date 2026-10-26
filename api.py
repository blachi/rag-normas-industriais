"""API HTTP + tela do assistente de normas.

    .venv\\Scripts\\python.exe -m uvicorn api:app --port 8010
    abrir http://127.0.0.1:8010            (tela)
    GET   http://127.0.0.1:8010/perguntar?q=quem pode assinar o prontuario eletrico
"""
from dataclasses import asdict

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from rag.responder import responde

app = FastAPI(title="Assistente de Normas Regulamentadoras", version="0.2")


@app.get("/perguntar")
def perguntar(q: str = Query(..., min_length=3, max_length=500)):
    return asdict(responde(q))


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
form{display:flex;gap:8px}input{flex:1;min-width:0;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg);font:inherit}
button{padding:12px 18px;border:0;border-radius:10px;background:var(--ac);color:#fff;font:inherit;cursor:pointer}
.ex{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 24px}.ex span{font-size:.85rem;border:1px solid var(--line);border-radius:99px;padding:4px 10px;cursor:pointer;color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:12px}
.cit{font-size:.85rem;color:var(--ac);font-weight:600;margin-bottom:6px}.sim{float:right;color:var(--mut);font-weight:400}
.aviso{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:10px 14px;margin-bottom:10px;font-size:.92rem}
.nao{color:var(--no)}.mut{color:var(--mut);font-size:.85rem}
</style></head><body><main>
<h1>Assistente de Normas Regulamentadoras</h1>
<p class="sub">Pergunte do jeito que falaria no chão de fábrica. A resposta vem com a norma e o item.</p>
<form id="f"><input id="q" placeholder="Ex.: posso usar aliança mexendo no painel?" autocomplete="off"><button>Perguntar</button></form>
<div class="ex" id="ex"></div><div id="out"></div>
<script>
const EX=["Posso trabalhar no painel usando aliança e relógio?","De quanto em quanto tempo refaço a reciclagem?","Eletricista pode trabalhar sozinho em alta tensão?","Quem pode assinar o prontuário elétrico?","Qual a receita de bolo de cenoura?"];
const ex=document.getElementById('ex');EX.forEach(t=>{const s=document.createElement('span');s.textContent=t;s.onclick=()=>{q.value=t;go()};ex.appendChild(s)});
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function go(){const v=q.value.trim();if(!v)return;out.innerHTML='<p class="mut">Buscando…</p>';
const r=await fetch('/perguntar?q='+encodeURIComponent(v)).then(r=>r.json());
if(!r.encontrou){out.innerHTML='<div class="card nao">'+esc(r.texto)+'</div>';return}
let h=r.avisos.map(a=>'<div class="aviso">⚠ '+esc(a)+'</div>').join('');
h+=r.fontes.map((f,i)=>'<div class="card"><div class="cit">'+(i?'':'Resposta · ')+esc(f.norma)+' — item '+esc(f.item)+' · p. '+f.pagina+'<span class="sim">similaridade '+f.similaridade.toFixed(3)+'</span></div>'+esc(f.texto)+'</div>').join('');
out.innerHTML=h}
document.getElementById('f').onsubmit=e=>{e.preventDefault();go()};
</script></main></body></html>"""


@app.get("/", response_class=HTMLResponse)
def tela():
    return TELA
