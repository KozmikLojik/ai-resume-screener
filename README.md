# AI Resume Screener

A small FastAPI and Streamlit application that extracts text from a PDF resume and estimates its semantic similarity to a job description. The score is an aid for reviewing documents; it is not a hiring recommendation.

## Run locally

Requires Python 3.11. The direct dependencies and model-loading stack are pinned in `requirements.txt`; the Hugging Face versions are kept together because Sentence Transformers relies on their APIs. PyArrow is pinned to a build compatible with the project's NumPy 1.24.3 pin. This is a pinned requirements set rather than a hash lock file, so pip still resolves compatible lower-level transitive packages.

```bash
git clone https://github.com/KozmikLojik/ai-resume-screener.git
cd ai-resume-screener
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements.txt
python run_api.py
```

In a second terminal, activate the same environment and run:

```bash
streamlit run app/streamlit_app.py
```

The API listens on `http://127.0.0.1:8000`. The Streamlit app uses `RESUME_API_URL` if set; otherwise it connects to that local API. The interactive API docs are available at `/docs`.

Resume uploads are limited to 10 MB and validated as PDFs. The API does not retain uploaded files after the request; bounded temporary spooling is described below.

## Upload limits and operational safeguards

The API accepts PDF files up to 10 MB, job descriptions up to 200,000 UTF-8 bytes, and PDFs with up to 100 pages. The `/match` request body is capped at the file limit plus the job-description limit and multipart overhead. Request bodies are spooled to a temporary file after 64 KB and the spool is closed after the request. The parser rejects encrypted, unreadable, and textless PDFs with client errors.

These application limits reduce per-request work; they are not complete protection against malicious PDFs or many concurrent requests. The service has no per-IP rate limiter. Configure request-rate limits and concurrency, memory, CPU, and request-time limits at the hosting or reverse-proxy layer. A shared rate-limit store would be needed for consistent limits across multiple app instances. Keep the service isolated and monitor temporary-disk capacity.

## Tests

After installing the requirements and activating the virtual environment, run:

```bash
python -m unittest discover -s tests -v
```

The unit tests use synthetic PDF content and mocked embeddings; they do not process personal résumés or evaluate real-world model accuracy. The `/match` API returns HTTP 400 with the same required-field message when the job description is missing, empty, or whitespace-only.

To explicitly test the downloaded pretrained model with synthetic text (the first run downloads model files), set the integration flag and run:

```bash
RUN_MODEL_INTEGRATION=1 python -m unittest tests.test_model_integration -v
```

In PowerShell, set the flag with `$env:RUN_MODEL_INTEGRATION="1"` before running the command. This integration check verifies that a related synthetic role scores above an unrelated one; it does not measure hiring accuracy.

## Deployment configuration

Deploy the API and Streamlit interface as separate services. For a container host such as Render, build the API with `deploy/Dockerfile`; the image binds to `0.0.0.0` and uses the host-provided `PORT` when available. Configure these variables in the hosting provider:

| Service | Variable | Value |
| --- | --- | --- |
| API | `CORS_ORIGINS` | The exact public Streamlit app origin, for example `https://your-app.streamlit.app` |
| API | `HOST` | `0.0.0.0` (already set by the Docker image) |
| Streamlit | `RESUME_API_URL` | The public API base URL, without `/match`, for example `https://your-api.onrender.com` |

The API loads the sentence-transformer model when the service starts. Allow time and memory for the model download and initialization. The deployment Dockerfile installs the CPU-only PyTorch wheel to avoid downloading GPU/CUDA libraries; this reduces unnecessary image size but does not guarantee the model will fit within a 512 MB memory limit. Do not expose resume contents or secrets in logs. A successful build or `/health` response alone does not verify the upload-to-report workflow; test that workflow before sharing the deployment.

## Docker

Build and run the API container from the repository root:

```bash
docker build -f deploy/Dockerfile -t ai-resume-screener .
docker run --rm -p 8000:8000 ai-resume-screener
```
