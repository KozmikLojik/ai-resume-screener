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

## Docker

Build and run the API container from the repository root:

```bash
docker build -f deploy/Dockerfile -t ai-resume-screener .
docker run --rm -p 8000:8000 ai-resume-screener
```
