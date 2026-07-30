from __future__ import annotations

from pathlib import Path

from magic_optimizer.match_oracle.health import forge_available


def test_forge_available_true_when_jar_exists(tmp_path: Path):
    jar = tmp_path / "forge.jar"
    jar.write_text("fake")
    assert forge_available(jar=str(jar)) is True


def test_forge_available_false_when_jar_missing(tmp_path: Path):
    assert forge_available(jar=str(tmp_path / "missing.jar")) is False


def test_forge_available_uses_forge_jar_env(tmp_path: Path, monkeypatch):
    jar = tmp_path / "env-forge.jar"
    jar.write_text("fake")
    monkeypatch.setenv("FORGE_JAR", str(jar))
    assert forge_available() is True


def test_forge_available_false_when_env_unset(monkeypatch):
    monkeypatch.delenv("FORGE_JAR", raising=False)
    assert forge_available() is False
