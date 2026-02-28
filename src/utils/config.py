from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from utils.settings import Settings


def _deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _interpolate_env(obj: Any) -> Any:
    if isinstance(obj, str):
        import re

        def repl(m: re.Match) -> str:
            key = m.group(1)
            return os.environ.get(key, "")

        return re.sub(r"\$\{([A-Z0-9_]+)\}", repl, obj)
    if isinstance(obj, list):
        return [_interpolate_env(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _interpolate_env(v) for k, v in obj.items()}
    return obj


def load_settings() -> Settings:
    # Load .env first so YAML interpolation can see env vars.
    load_dotenv(override=False)

    env = os.environ.get("RAG_ENV", "dev")
    config_dir = Path(os.environ.get("RAG_CONFIG_DIR", "configs"))

    base_path = config_dir / "base.yaml"
    env_path = config_dir / f"{env}.yaml"

    if not base_path.exists():
        raise FileNotFoundError(f"Missing config file: {base_path}")

    base = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
    override = yaml.safe_load(env_path.read_text(encoding="utf-8")) if env_path.exists() else {}

    merged = _deep_merge(base, override or {})
    merged = _interpolate_env(merged)
    return Settings.model_validate(merged)


def ensure_dirs(settings: Settings) -> None:
    for p in [
        settings.paths.raw_dir,
        settings.paths.processed_dir,
        settings.paths.chunks_dir,
        settings.paths.metadata_dir,
        settings.paths.indexes_dir,
        # Common sub-indexes
        str(Path(settings.paths.indexes_dir) / "bm25"),
    ]:
        Path(p).mkdir(parents=True, exist_ok=True)
