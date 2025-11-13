import torch
from .embedder import get_embedding
from .preprocessor import clean_text
from typing import List, Dict

def match_resume_to_jd(resume_text: str, jd_text: str) -> float:
    """Return match percentage (0-100)"""
    clean_resume = clean_text(resume_text)
    clean_jd = clean_text(jd_text)
    
    emb1 = get_embedding(clean_resume)
    emb2 = get_embedding(clean_jd)
    
    # Cosine similarity
    similarity = torch.cosine_similarity(emb1, emb2, dim=0).item()
    return round(similarity * 100, 2)