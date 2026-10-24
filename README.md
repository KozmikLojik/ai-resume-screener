# AI Resume Screener

A small FastAPI and Streamlit application that extracts text from a PDF resume and estimates its semantic similarity to a job description. The score is an aid for reviewing documents; it is not a hiring recommendation.

## Run locally

Requires Python 3.10 or later.

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

Resume uploads are limited to 10 MB, validated as PDFs, and processed in memory. The API does not keep uploaded files.

## Tests

After installing the requirements and activating the virtual environment, run:

```bash
python -m unittest discover -s tests -v
```

The tests use synthetic PDF content and mocked embeddings; they do not process personal résumés or evaluate real-world model accuracy.

## Deployment configuration

Deploy the API and Streamlit interface as separate services. For a container host such as Render, build the API with `deploy/Dockerfile`; the image binds to `0.0.0.0` and uses the host-provided `PORT` when available. Configure these variables in the hosting provider:

| Service | Variable | Value |
| --- | --- | --- |
| API | `CORS_ORIGINS` | The exact public Streamlit app origin, for example `https://your-app.streamlit.app` |
| API | `HOST` | `0.0.0.0` (already set by the Docker image) |
| Streamlit | `RESUME_API_URL` | The public API base URL, without `/match`, for example `https://your-api.onrender.com` |

The API loads the sentence-transformer model when the service starts. Allow time and memory for the model download and initialization. Do not expose resume contents or secrets in logs. A successful build or `/health` response alone does not verify the upload-to-report workflow; test that workflow before sharing the deployment.

## Docker

Build and run the API container from the repository root:

```bash
docker build -f deploy/Dockerfile -t ai-resume-screener .
docker run --rm -p 8000:8000 ai-resume-screener
```
