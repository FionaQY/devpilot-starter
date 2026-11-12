from pathlib import Path

import pytest

from devpilot.tools.filesystem import RepositoryFiles, WorkspaceError


def test_reads_file_inside_repository(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("hello DevPilot", encoding="utf-8")
    files = RepositoryFiles(tmp_path)
    assert files.read_file("hello.txt") == "hello DevPilot"


def test_rejects_path_traversal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    files = RepositoryFiles(repo)

    with pytest.raises(WorkspaceError):
        files.read_file("../secret.txt")


def test_lists_files_and_searches(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def main():\n    return 'hello'\n", encoding="utf-8")
    files = RepositoryFiles(tmp_path)

    assert "src/app.py" in files.list_files()
    assert "src/app.py:2" in files.search_files("hello")
