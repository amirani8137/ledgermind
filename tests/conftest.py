import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
STATEMENTS = EXAMPLES / "statements"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A throwaway copy of the examples folder (so tests never touch the repo)."""
    dest = tmp_path / "ws"
    shutil.copytree(EXAMPLES, dest, ignore=shutil.ignore_patterns("import-*.beancount", "*.rejected"))
    return dest
