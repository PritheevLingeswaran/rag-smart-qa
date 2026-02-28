from __future__ import annotations

from scripts.build_index import build_index_main
from scripts.ingest_data import ingest_main
from scripts.run_eval import run_eval_main


def run_all_main() -> None:
    ingest_main()
    build_index_main()
    run_eval_main()


if __name__ == "__main__":
    run_all_main()
