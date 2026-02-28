from __future__ import annotations

import argparse

from ingestion.ingest import ingest_documents, write_chunks
from scripts.build_index import build_index_main
from scripts.run_api import run_api_main
from scripts.run_eval import run_eval_main
from utils.config import ensure_dirs, load_settings
from utils.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(prog="rag-smart-qa")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    sub.add_parser("build-index")
    sub.add_parser("serve")
    sub.add_parser("eval")
    args = parser.parse_args()

    settings = load_settings()
    ensure_dirs(settings)
    configure_logging()

    if args.cmd == "ingest":
        chunks = ingest_documents(settings)
        write_chunks(settings, chunks)
    elif args.cmd == "build-index":
        build_index_main()
    elif args.cmd == "serve":
        run_api_main()
    elif args.cmd == "eval":
        run_eval_main()


if __name__ == "__main__":
    main()
