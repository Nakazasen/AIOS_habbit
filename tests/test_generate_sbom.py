from pathlib import Path
import importlib.util


class FakeDistribution:
    def __init__(self, name: str, version: str):
        self.metadata = {"Name": name}
        self.name = name
        self.version = version


def load_sbom_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "generate_sbom.py"
    spec = importlib.util.spec_from_file_location("generate_sbom", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_build_sbom_is_sorted_and_has_no_path_metadata():
    module = load_sbom_module()
    sbom = module.build_sbom([FakeDistribution("zeta_pkg", "2.0"), FakeDistribution("Alpha", "1.0")])
    assert sbom["bomFormat"] == "CycloneDX"
    assert [component["name"] for component in sbom["components"]] == ["Alpha", "zeta_pkg"]
    assert all("path" not in component for component in sbom["components"])
