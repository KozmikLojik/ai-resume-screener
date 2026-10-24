"""Opt-in smoke test for the downloaded pretrained sentence-transformer."""

import math
import os
import unittest


@unittest.skipUnless(
    os.getenv("RUN_MODEL_INTEGRATION") == "1",
    "set RUN_MODEL_INTEGRATION=1 to download and run the real model",
)
class ModelIntegrationTests(unittest.TestCase):
    def test_real_model_scores_related_synthetic_role_higher(self):
        from src.matcher import match_resume_to_jd

        resume = (
            "Software engineer with five years building backend services using Python, "
            "FastAPI, PostgreSQL, Docker, and AWS. Designed REST APIs and automated tests."
        )
        related_job = (
            "Backend engineer experienced in Python, FastAPI, REST APIs, PostgreSQL, "
            "Docker, cloud deployment, and automated testing."
        )
        unrelated_job = (
            "Registered pediatric nurse providing clinical care, administering medication, "
            "coordinating with families, and documenting patient outcomes."
        )

        related_score = match_resume_to_jd(resume, related_job)
        unrelated_score = match_resume_to_jd(resume, unrelated_job)
        empty_score = match_resume_to_jd("", related_job)

        for score in (related_score, unrelated_score, empty_score):
            self.assertTrue(math.isfinite(score))
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)
        self.assertGreater(related_score, unrelated_score)
        self.assertEqual(empty_score, 0.0)


if __name__ == "__main__":
    unittest.main()
