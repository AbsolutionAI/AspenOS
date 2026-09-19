import shutil
import yaml
from pathlib import Path

import pytest

import plugin_manager as pm
from plugin_manager import PluginManager


def _make_plugin(source: Path, name: str, version: str, marker: str = "") -> None:
    source.mkdir(parents=True, exist_ok=True)
    (source / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": name,
                "version": version,
                "description": "test plugin",
                "author": "test",
            }
        )
    )
    marker = marker or version
    (source / "__init__.py").write_text(f"# {name} {marker}\n")


def _make_manager(tmp_path: Path) -> PluginManager:
    cfg = tmp_path / "plugins.yaml"
    cfg.write_text(yaml.safe_dump({"plugins": {"dir": str(tmp_path / "installed")}}))
    return PluginManager(config_path=cfg)


class TestUpdate:
    def test_update_replaces_installed_plugin(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        assert manager.install_from_path(source, "demo") is True
        assert (manager.plugins_dir / "demo" / "__init__.py").read_text().endswith("0.1.0\n")

        newer = tmp_path / "src2"
        _make_plugin(newer, "demo", "0.2.0", marker="0.2.0")
        (newer / "extra.txt").write_text("new feature\n")

        assert manager.update("demo", newer) is True
        assert (manager.plugins_dir / "demo" / "extra.txt").exists()
        assert (manager.plugins_dir / "demo" / "__init__.py").read_text().endswith("0.2.0\n")
        assert manager.states["demo"].version == "0.2.0"

    def test_update_requires_known_plugin(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        assert manager.update("unknown", source) is False
        assert manager.update("demo", source) is False  # same version no-op

    def test_update_source_must_be_directory(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        assert manager.update("demo", tmp_path / "nope") is False
        assert manager.update("demo", tmp_path / "file.txt") is False

    def test_update_requires_matching_name(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        other = tmp_path / "other"
        _make_plugin(other, "other", "0.2.0")
        assert manager.update("demo", other) is False
        assert manager.states["demo"].version == "0.1.0"

    def test_update_refuses_downgrade(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.2.0")
        manager.install_from_path(source, "demo")

        older = tmp_path / "old"
        _make_plugin(older, "demo", "0.1.0")
        assert manager.update("demo", older) is False
        assert manager.states["demo"].version == "0.2.0"

    def test_update_refuses_same_version_without_force(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        same = tmp_path / "same"
        _make_plugin(same, "demo", "0.1.0", marker="replaced")
        assert manager.update("demo", same) is False
        assert not (manager.plugins_dir / "demo" / "__init__.py").read_text().endswith("replaced\n")

    def test_update_force_allows_same_version(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        same = tmp_path / "same"
        _make_plugin(same, "demo", "0.1.0", marker="replaced")
        assert manager.update("demo", same, force=True) is True
        assert (manager.plugins_dir / "demo" / "__init__.py").read_text().endswith("replaced\n")

    def test_update_without_source_keeps_marketplace_stub(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        assert manager.update("demo") is False
        assert manager.states["demo"].version == "0.1.0"

    def test_update_missing_manifest(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        empty = tmp_path / "empty"
        empty.mkdir()
        assert manager.update("demo", empty) is False

    def test_cli_update_command_registered(self, tmp_path, capsys):
        manager = _make_manager(tmp_path)
        source = tmp_path / "src"
        _make_plugin(source, "demo", "0.1.0")
        manager.install_from_path(source, "demo")

        new = tmp_path / "new-src"
        _make_plugin(new, "demo", "0.3.0")
        pm.cmd_update(manager, ["demo", str(new)])
        out = capsys.readouterr().out
        assert "Updated plugin 'demo' v0.3.0" in out
        assert manager.states["demo"].version == "0.3.0"

    def test_cli_update_usage(self, tmp_path, capsys):
        manager = _make_manager(tmp_path)
        pm.cmd_update(manager, ["demo"])
        assert "Usage:" in capsys.readouterr().out

    def test_install_then_update_plugin_manager_modules_touch(self, tmp_path):
        assert hasattr(pm.PluginManager, "update")
        assert hasattr(pm, "cmd_update")