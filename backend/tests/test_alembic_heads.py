import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def find_alembic_ini() -> str:
    here = Path(__file__).resolve().parent
    candidate = (here.parent / "alembic.ini").resolve()
    if candidate.exists():
        return str(candidate)
    cwd_candidate = Path(os.getcwd()) / "alembic.ini"
    if cwd_candidate.exists():
        return str(cwd_candidate.resolve())
    raise FileNotFoundError("alembic.ini not found")


def test_alembic_has_single_head() -> None:
    cfg = Config(find_alembic_ini())
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert isinstance(heads, list)
    assert len(heads) == 1, f"Expected a single alembic head, found: {heads}"
