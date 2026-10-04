import torch

from .embedder import get_embedding
from .preprocessor import clean_text


def match_resume_to_jd(resume_text: str, jd_text: str) -> float:
    """Return a bounded cosine-similarity score from 0 to 100."""
    clean_resume = clean_text(resume_text)
    clean_jd = clean_text(jd_text)
    if not clean_resume or not clean_jd:
        return 0.0

    resume_embedding = get_embedding(clean_resume)
    job_embedding = get_embedding(clean_jd)
    similarity = torch.cosine_similarity(resume_embedding, job_embedding, dim=0).item()
    return round(max(0.0, min(100.0, similarity * 100)), 2)
