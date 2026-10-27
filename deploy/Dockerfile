FROM python:3.11-slim

WORKDIR /app
ENV HOST=0.0.0.0
ENV HF_HUB_DISABLE_TELEMETRY=1
ENV TOKENIZERS_PARALLELISM=false

COPY requirements.txt .
# Install the CPU-only PyTorch wheel so deployment does not pull GPU/CUDA libraries.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.14.1+cpu" \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY run_api.py .
EXPOSE 8000
CMD ["python", "run_api.py"]
