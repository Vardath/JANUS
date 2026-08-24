"""Static contract tests for JANUS topology and deploy bootstrapping."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureContractTests(unittest.TestCase):
    def test_canonical_topology_lives_in_server_v2(self):
        topology = (ROOT / "server_v2" / "topology.py").read_text(encoding="utf-8")
        protocol = (ROOT / "server_v2" / "protocol.py").read_text(encoding="utf-8")
        entrypoint = (ROOT / "server_v2" / "entrypoint.py").read_text(encoding="utf-8")
        self.assertIn('"1-3-7:', topology)
        self.assertIn('MECHANICAL_FLOW = "7 -> 2 -> 1 -> 1"', topology)
        self.assertIn('FRONT_CORE = "front"', topology)
        self.assertIn('"conceptual_topology": "1|3|7"', protocol)
        self.assertIn('"canonical_core_total": 11', protocol)
        self.assertIn('"legacy_consensus_alias_is_core": False', protocol)
        self.assertNotIn("dashboard_api", entrypoint)

    def test_original_seven_have_canonical_fano_home_positions(self):
        topology = (ROOT / "server_v2" / "topology.py").read_text(encoding="utf-8")
        for name, direction in (
            ("evidence", 1), ("safety", 2), ("counterpoint", 3), ("context", 4),
            ("logic", 5), ("novelty", 6), ("memory", 7),
        ):
            self.assertIn(f'"{name}": SpecialistRole(', topology)
            self.assertIn(f'"{name}", {direction},', topology)
        self.assertIn("receive all seven subconscious projections", topology)

    def test_final_health_routes_are_architecture_aware(self):
        api = (ROOT / "server_v2" / "architecture_api.py").read_text(encoding="utf-8")
        entrypoint = (ROOT / "server_v2" / "entrypoint.py").read_text(encoding="utf-8")
        self.assertIn('"conceptual_topology": "1|3|7"', api)
        self.assertIn('"mechanical_flow": "7 -> 2 -> 1 -> 1"', api)
        self.assertIn('"core_count": 11', api)
        self.assertIn('(\"/health\",\"GET\")', entrypoint)
        self.assertIn("architecture_router", entrypoint)

    def test_render_rebuilds_base_server_before_boot(self):
        text = (ROOT / "render.yaml").read_text(encoding="utf-8")
        self.assertIn("python tools/rebuild_server.py", text)
        self.assertIn("uvicorn janus_app:app", text)

    def test_docker_rebuilds_base_server_before_boot(self):
        text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("RUN python tools/rebuild_server.py", text)
        self.assertIn("uvicorn janus_app:app", text)
        self.assertNotIn("patch_url_media_ingestion.py", text)

    def test_server_fragments_exist(self):
        parts = sorted((ROOT / "src").glob("server.py.gz.b64.*"))
        self.assertGreaterEqual(len(parts), 1)


if __name__ == "__main__":
    unittest.main()
