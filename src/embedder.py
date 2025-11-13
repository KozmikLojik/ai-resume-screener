from sentence_transformers import SentenceTransformer
import torch

# Load model once
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str):
    """Return 384-dim embedding"""
    return model.encode(text, convert_to_tensor=True)