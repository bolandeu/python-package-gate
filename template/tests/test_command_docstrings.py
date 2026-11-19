"""The command docstrings: the checker the project's checks run over `commands/*.py`."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"



def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module



def test_docstring_check_reads_the_working_tree_only() -> None:
    import inspect

    check = _load("check_command_docstrings")
    assert list(inspect.signature(check.stale_commands).parameters) == ["paths"]
    assert "index" not in (check.stale_commands.__doc__ or "")



def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


COMMAND = "src/demo/commands/greet.py"
GREET = '''import typer
from demo import output

@output.guard
def greet(name: str) -> None:
    """Say hello to NAME.

    Example: {cli} greet bob
    """
    print(f"hello {name}")
'''



def _docstring_check(tmp_path: Path, edited: str) -> int:
    """Run the checker on a repo whose only command is committed, then edited: its exit code."""
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / COMMAND).parent.mkdir(parents=True)
    (tmp_path / COMMAND).write_text(GREET)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "add greet")
    (tmp_path / COMMAND).write_text(edited)
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        return _load("check_command_docstrings").main([])
    finally:
        os.chdir(cwd)



def test_docstring_check_ignores_a_ctx_only_signature_change(tmp_path: Path) -> None:
    edited = GREET.replace("def greet(name: str)", "def greet(ctx: typer.Context, name: str)")
    assert _docstring_check(tmp_path, edited) == 0



def test_docstring_check_catches_a_real_argument_change(tmp_path: Path) -> None:
    edited = GREET.replace("def greet(name: str)", "def greet(name: str, times: int)")
    assert _docstring_check(tmp_path, edited) == 1



def test_env_files_are_ignored(tmp_path: Path) -> None:
    shutil.copy(SCRIPTS.parent / ".gitignore", tmp_path / ".gitignore")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "i")
    (tmp_path / ".env").write_text("TOKEN=x\n")
    (tmp_path / ".env.local").write_text("TOKEN=y\n")
    assert _git(tmp_path, "status", "--porcelain", "--untracked-files=all") == ""


GITEA_INDEX = "https://homeserver.tailee01ab.ts.net:3000/api/packages/bolandeu/pypi/simple"



def test_project_declares_the_gitea_index_explicit() -> None:
    import tomllib

    config = tomllib.loads((SCRIPTS.parent / "pyproject.toml").read_text())
    assert {"name": "gitea", "url": GITEA_INDEX, "explicit": True} in config["tool"]["uv"]["index"]
