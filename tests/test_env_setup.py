import importlib.util
from scripts import setup as setup_script


def test_pytest_importable() -> None:
    assert importlib.util.find_spec("pytest") is not None


def test_install_requirements_uses_dev_file(monkeypatch, tmp_path) -> None:
    called = []

    def fake_run(cmd: list[str], dry_run: bool) -> None:
        called.append(cmd)

    monkeypatch.setattr(setup_script, "run", fake_run)
    setup_script.install_requirements(tmp_path, dry_run=False)
    assert any("requirements-dev.txt" in part for part in called[0])
