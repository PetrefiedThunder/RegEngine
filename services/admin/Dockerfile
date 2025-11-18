FROM python:3.11-slim

WORKDIR /app

# Copy shared modules
COPY shared/ /app/shared/

# Copy service files
COPY services/admin/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/admin/ .

EXPOSE 8400

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8400/health').read()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8400"]
