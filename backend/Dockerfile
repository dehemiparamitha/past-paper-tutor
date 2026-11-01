
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

# Install CPU-only PyTorch first to avoid unnecessary CUDA packages.
RUN python -m pip install --upgrade pip \
    && python -m pip install \
    --no-cache-dir \
    --retries 10 \
    --timeout 120 \
    torch \
    --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install \
    --no-cache-dir \
    --retries 10 \
    --timeout 120 \
    -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
