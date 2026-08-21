"""Static contract tests for JANUS topology and deploy bootstrapping."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureContractTests(unittest.TestCase):
    def test_dashboard_uses_current_topology(self):
        text = (ROOT / "dashboard_api.py").read_text(encoding="utf-8")
        self.assertIn("7 -> 2 -> 1 -> 1", text)
        self.assertNotIn("7 -> 3 -> 1", text)
        self.assertIn("core_count\": 11", text)

    def test_render_rebuilds_base_server_before_boot(self):
        text = (ROOT / "render.yaml").read_text(encoding="utf-8")
        self.assertIn("python tools/rebuild_server.py", text)
        self.assertIn("uvicorn bootstrap:app", text)

    def test_docker_rebuilds_base_server_before_boot(self):
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("RUN python tools/rebuild_server.py", text)
        self.assertIn("uvicorn bootstrap:app", text)

    def test_server_fragments_exist(self):
        parts = sorted((ROOT / "src").glob("server.py.gz.b64.*"))
        self.assertGreaterEqual(len(parts), 1)


if __name__ == "__main__":
    unittest.main()
