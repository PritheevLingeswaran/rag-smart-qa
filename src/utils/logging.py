from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Any

import structlog
import yaml


def configure_logging(config_path: str = "configs/logging.yaml", level: str = "INFO") -> None:
    p = Path(config_path)
    if p.exists():
        cfg: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        logging.config.dictConfig(cfg)
    else:
        logging.basicConfig(level=getattr(logging, level, logging.INFO), format="%(message)s")

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level, logging.INFO)),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "rag-smart-qa") -> structlog.BoundLogger:
    return structlog.get_logger(name)
