from pathlib import Path


class WorkspaceError(ValueError):
    pass


class RepositoryFiles:
    """Read-only filesystem access restricted to one repository root."""

    def __init__(self, root: Path, max_file_chars: int = 20_000) -> None:
        self.root = root.resolve()
        self.max_file_chars = max_file_chars
        if not self.root.is_dir():
            raise WorkspaceError(f"Repository directory does not exist: {self.root}")

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise WorkspaceError("Path is outside the selected repository.")
        return candidate

    def list_files(self, directory: str = ".", limit: int = 200) -> str:
        target = self._resolve(directory)
        if not target.is_dir():
            raise WorkspaceError(f"Not a directory: {directory}")

        ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".next"}
        entries = []
        for path in sorted(target.rglob("*")):
            if path.is_symlink() or any(part in ignored for part in path.relative_to(self.root).parts):
                continue
            if path.is_file():
                entries.append(str(path.relative_to(self.root)))
                if len(entries) >= min(max(limit, 1), 500):
                    break

        return "\n".join(entries) if entries else "(No files found.)"

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise WorkspaceError(f"File not found: {path}")
        if target.stat().st_size > self.max_file_chars * 4:
            raise WorkspaceError("File is too large to read in one operation.")

        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > self.max_file_chars:
            content = content[: self.max_file_chars] + "\n\n[Truncated by DevPilot.]"
        return content

    def search_files(self, query: str, limit: int = 50) -> str:
        if not query.strip():
            raise WorkspaceError("Search query cannot be empty.")

        ignored = {".git", ".venv", "venv", "__pycache__", "node_modules", ".next"}
        matches = []
        for path in self.root.rglob("*"):
            if path.is_symlink() or not path.is_file() or any(part in ignored for part in path.relative_to(self.root).parts):
                continue
            try:
                if path.stat().st_size > 1_000_000:
                    continue
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue

            for line_number, line in enumerate(lines, start=1):
                if query.casefold() in line.casefold():
                    relative = path.relative_to(self.root)
                    matches.append(f"{relative}:{line_number}: {line[:300]}")
                    if len(matches) >= min(max(limit, 1), 100):
                        return "\n".join(matches)

        return "\n".join(matches) if matches else "(No matches found.)"
