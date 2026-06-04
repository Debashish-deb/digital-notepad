import unittest
import requests

class TestCopilotPlatform(unittest.TestCase):
    API_URL = "http://localhost:8000"

    def test_health(self):
        """Verifies backend is healthy and database is connected."""
        r = requests.get(f"{self.API_URL}/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["database_connected"])

    def test_qa_queries(self):
        """Executes the 14 required researcher test cases and validates outputs."""
        test_queries = [
            "Install napari on macOS Apple Silicon.",
            "Install Cylinter on Linux workstation.",
            "My napari crashes with OpenGL error. Fix it.",
            "Generate a LUMI Slurm script for Mesmer segmentation.",
            "Run Ashlar after BaSiC correction.",
            "What files do I need before Cylinter QC?",
            "Check this Slurm error and tell me what failed.",
            "Create a conda environment for StarDist.",
            "Generate a safe quantification script.",
            "Explain our tCyCIF pipeline from raw image to downstream analysis.",
            "Find all SOPs related to segmentation.",
            "How do I run this on Windows using WSL2?",
            "Compare Mesmer vs StarDist for dense tissue.",
            "Create a project checklist before processing new samples."
        ]

        for q in test_queries:
            with self.subTest(query=q):
                payload = {
                    "question": q,
                    "project_codes": ["SPACE", "EyeMT"],
                    "mode": "documentation_only"
                }
                r = requests.post(f"{self.API_URL}/ask", json=payload)
                self.assertEqual(r.status_code, 200)
                res = r.json()
                self.assertTrue(res["is_safe"])
                self.assertIsNotNone(res["answer"])
                self.assertTrue(len(res["answer"]) > 20)

    def test_install_recipes(self):
        """Tests the recipe generator endpoint."""
        payload = {"tool_name": "napari", "os_platform": "linux"}
        r = requests.post(f"{self.API_URL}/install_guide", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("mamba install", data["script"])

    def test_lumi_script_builder(self):
        """Tests the Slurm generation endpoint."""
        payload = {
            "job_name": "test_job",
            "project_account": "project_462001415",
            "use_gpu": True
        }
        r = requests.post(f"{self.API_URL}/lumi_job", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("#SBATCH --job-name=test_job", data["script"])

    def test_log_parser(self):
        """Tests troubleshooting log analysis endpoint."""
        payload = {"log_text": "Slurm task terminated: Out of memory (exit code 137)"}
        r = requests.post(f"{self.API_URL}/parse_log", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("OOM", data["cause"])

    def test_environment_checkers(self):
        """Tests executing local environment checks."""
        payload = {"checker_name": "python_env"}
        r = requests.post(f"{self.API_URL}/run_checker", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("status", data)
        self.assertIn("stdout", data)

if __name__ == "__main__":
    unittest.main()
