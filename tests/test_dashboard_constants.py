"""Tests for dashboard constants environment overrides."""

from __future__ import annotations

import importlib
import scripts.dashboard.constants as dash_constants


DEFAULT_CONFIG_DIR = dash_constants.CONFIG_DIR
DEFAULT_CONFIG_JSON = dash_constants.CONFIG_JSON
DEFAULT_ROOT = dash_constants.ROOT


def _reload_constants():
    return importlib.reload(dash_constants)


def test_config_json_env_override(monkeypatch, tmp_path):
    custom_path = (tmp_path / "custom.json").resolve()
    monkeypatch.setenv("GMAIL_AUTOMATION_CONFIG_JSON", str(custom_path))

    reloaded = _reload_constants()
    assert reloaded.CONFIG_JSON == custom_path
    assert reloaded.CONFIG_DIR == custom_path.parent

    monkeypatch.delenv("GMAIL_AUTOMATION_CONFIG_JSON", raising=False)
    restored = _reload_constants()
    assert restored.CONFIG_JSON == DEFAULT_CONFIG_JSON
    assert restored.CONFIG_DIR == DEFAULT_CONFIG_DIR


def test_config_dir_env_override(monkeypatch, tmp_path):
    custom_dir = (tmp_path / "config" / "nested").resolve()
    monkeypatch.setenv("GMAIL_AUTOMATION_CONFIG_DIR", str(custom_dir))

    reloaded = _reload_constants()
    expected_json = custom_dir / "gmail_config-final.json"
    assert reloaded.CONFIG_DIR == custom_dir
    assert reloaded.CONFIG_JSON == expected_json

    monkeypatch.delenv("GMAIL_AUTOMATION_CONFIG_DIR", raising=False)
    restored = _reload_constants()
    assert restored.CONFIG_JSON == DEFAULT_CONFIG_JSON
    assert restored.CONFIG_DIR == DEFAULT_CONFIG_DIR


def test_dashboard_root_env_override(monkeypatch, tmp_path):
    custom_root = (tmp_path / "alt_root").resolve()
    monkeypatch.setenv("GMAIL_AUTOMATION_DASHBOARD_ROOT", str(custom_root))

    reloaded = _reload_constants()
    assert reloaded.ROOT == custom_root
    assert reloaded.CONFIG_DIR == custom_root / "config"
    assert reloaded.CONFIG_JSON == reloaded.CONFIG_DIR / "gmail_config-final.json"

    monkeypatch.delenv("GMAIL_AUTOMATION_DASHBOARD_ROOT", raising=False)
    restored = _reload_constants()
    assert restored.ROOT == DEFAULT_ROOT
    assert restored.CONFIG_DIR == DEFAULT_CONFIG_DIR
