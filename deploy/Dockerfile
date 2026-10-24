FROM python:3.11-slim

WORKDIR /app
ENV HOST=0.0.0.0
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY run_api.py .
EXPOSE 8000
CMD ["python", "run_api.py"]
