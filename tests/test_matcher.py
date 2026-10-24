import importlib
import math
import sys
import types
import unittest
from unittest.mock import patch


class FakeScore:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


def cosine_similarity(left, right, dim=0):
    del dim
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    return FakeScore(dot / (norm_left * norm_right))


class MatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch_stub = types.ModuleType("torch")
        torch_stub.cosine_similarity = cosine_similarity
        embedder_stub = types.ModuleType("src.embedder")
        embedder_stub.get_embedding = lambda _text: [1.0, 0.0]
        with patch.dict(sys.modules, {"torch": torch_stub, "src.embedder": embedder_stub}):
            cls.matcher = importlib.import_module("src.matcher")

    def test_empty_resume_or_job_description_returns_zero_without_embedding(self):
        with patch.object(self.matcher, "get_embedding") as get_embedding:
            self.assertEqual(self.matcher.match_resume_to_jd("   ", "Python developer"), 0.0)
            self.assertEqual(self.matcher.match_resume_to_jd("Python engineer", "\n"), 0.0)
            get_embedding.assert_not_called()

    def test_synthetic_identical_embeddings_return_full_similarity(self):
        with patch.object(self.matcher, "get_embedding", return_value=[1.0, 0.0]):
            self.assertEqual(self.matcher.match_resume_to_jd("Python data", "Python data"), 100.0)

    def test_synthetic_orthogonal_embeddings_return_zero_similarity(self):
        with patch.object(self.matcher, "get_embedding", side_effect=[[1.0, 0.0], [0.0, 1.0]]):
            self.assertEqual(self.matcher.match_resume_to_jd("Python data", "French cooking"), 0.0)


if __name__ == "__main__":
    unittest.main()
