# Imagem da API. Os PDFs NAO vao na imagem (fonte oficial, nao redistribuida):
# monte a pasta com eles em /app/data/raw e o container corta e indexa na 1a subida.
#
#   docker build -t rag-normas .
#   docker run -p 8010:8010 -v "%cd%/data/raw:/app/data/raw:ro" -v rag-dados:/app/data/chroma rag-normas
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ANONYMIZED_TELEMETRY=False \
    HF_HOME=/app/.cache/huggingface
WORKDIR /app

# torch so CPU: a imagem com CUDA passaria de 5 GB para nada
RUN pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# baixa os dois modelos no build: a 1a pergunta nao espera download
# (embeddings ~470 MB + cross-encoder bge-reranker-v2-m3 ~2,1 GB)
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('intfloat/multilingual-e5-small'); CrossEncoder('BAAI/bge-reranker-v2-m3')"

COPY rag/ rag/
COPY eval/ eval/
COPY api.py docker-entrypoint.sh ./
COPY data/catalogo.json data/

RUN useradd --create-home app && chown -R app /app && chmod +x docker-entrypoint.sh
USER app
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/saude')"
ENTRYPOINT ["./docker-entrypoint.sh"]
