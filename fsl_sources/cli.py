"""CLI for public benchmark and community evidence import (v0.3).

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

from .adapters import (
    ARENA_DATASET, arena_rows_request, arena_splits_request,
    hf_benchmark_request, hf_model_request, json_api_get,
    parse_arena_page, parse_community_rollup,
    parse_hf_benchmark, parse_hf_model,
)
from .catalog import (
    CatalogError, add_alias, connect, iso_day,
    list_observations, model_dossier, save_snapshot, trend,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True,
                     allow_nan=False))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Multi-source observations; no raw personal reviews or capability scalar")
    parser.add_argument("--db", default="data/fsl_adaptive.sqlite",
                        help="Shared SQLite database with the adaptive engine")
    parser.add_argument("--retrieved-on", default=date.today().isoformat(),
                        help="Date this source was actually obtained YYYY-MM-DD")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="create multichannel tables")

    hf = commands.add_parser("hf-model", help="import HF Hub model metadata")
    hf.add_argument("--id", required=True, help="namespace/model")
    hf.add_argument("--offline-json", help="load fixture; not independently verified")

    splits = commands.add_parser("arena-splits", help="inspect live Arena subsets")
    splits.add_argument("--offline-json", help="load fixture instead of network")

    arena = commands.add_parser("arena", help="import one Arena dataset-viewer page")
    arena.add_argument("--config", default="text", help="sub-dataset, e.g. text/agent")
    arena.add_argument("--split", default="latest", choices=("latest", "full"))
    arena.add_argument("--offset", type=int, default=0)
    arena.add_argument("--limit", type=int, default=100)
    arena.add_argument("--offline-json", help="load fixture; not independently verified")

    bench = commands.add_parser("hf-benchmark", help="import HF official benchmark leaderboard")
    bench.add_argument("--dataset", required=True)
    bench.add_argument("--offline-json", help="load fixture; not independently verified")

    reviews = commands.add_parser("community", help="ingest aggregate-only, sourced feedback JSON")
    reviews.add_argument("--file", required=True)

    alias = commands.add_parser("alias", help="manually link cross-platform model identities")
    alias.add_argument("--source-type", required=True,
                       choices=("hf_model", "arena", "hf_benchmark", "community_rollup"))
    alias.add_argument("--external-id", required=True)
    alias.add_argument("--canonical-key", required=True)
    alias.add_argument("--source-url", required=True)

    obs = commands.add_parser("observations", help="view numerical observations by channel")
    obs.add_argument("--model-id")
    obs.add_argument("--channel", choices=("metadata", "preference", "benchmark", "community"))
    obs.add_argument("--limit", type=int, default=100)
    obs.add_argument("--as-of", help="hide data retrieved after this date")

    series = commands.add_parser("trend", help="compare *one exact methodological stratum*")
    series.add_argument("--model-id", required=True)
    series.add_argument("--measure", required=True)
    series.add_argument("--category", required=True)
    series.add_argument("--methodology", required=True)
    series.add_argument("--channel", required=True,
                        choices=("metadata", "preference", "benchmark", "community"))
    series.add_argument("--as-of", help="hide hindsight knowledge")
    dossier = commands.add_parser("dossier", help="combine manually matched identities without mixing scores")
    dossier.add_argument("--canonical-key", required=True)
    dossier.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)
    try:
        retrieved = iso_day(args.retrieved_on, "retrieved_on")
        # A live API call is a present-day observation. Refuse to create
        # historical source records by fetching today's API while backdating it.
        if args.command in ("hf-model", "arena", "hf-benchmark", "arena-splits"):
            if not args.offline_json and retrieved != date.today().isoformat():
                raise CatalogError("live API fetches must use the actual retrieval date")
        if args.command == "arena-splits":
            data = read_json(args.offline_json) if args.offline_json else json_api_get(
                arena_splits_request())
            if not isinstance(data, dict) or not isinstance(data.get("splits"), list):
                raise CatalogError("expected Arena viewer splits response")
            split_pairs = sorted({(x.get("config"), x.get("split"))
                                  for x in data["splits"] if isinstance(x, dict)
                                  and isinstance(x.get("config"), str)
                                  and isinstance(x.get("split"), str)})
            emit({"dataset": ARENA_DATASET,
                  "config_splits": [{"config": c, "split": s} for c, s in split_pairs],
                  "count": len(split_pairs)})
            return 0

        with connect(args.db) as db:
            if args.command == "init":
                emit({"database": args.db, "schema": "fsl/sources/0.3"})
                return 0
            if args.command == "observations":
                emit(list_observations(db, model_id=args.model_id,
                                       channel=args.channel, limit=args.limit,
                                       as_of=args.as_of))
                return 0
            if args.command == "trend":
                emit(trend(db, model_id=args.model_id, measure=args.measure,
                           category=args.category, methodology=args.methodology,
                           channel=args.channel, as_of=args.as_of))
                return 0
            if args.command == "dossier":
                emit(model_dossier(db, canonical_model_key=args.canonical_key,
                                   as_of=args.as_of))
                return 0
            if args.command == "alias":
                emit({"alias_id": add_alias(
                    db, source_type=args.source_type,
                    external_model_id=args.external_id,
                    canonical_model_key=args.canonical_key,
                    source=args.source_url, recorded_on=retrieved)})
                return 0

            if args.command == "community":
                prepared = parse_community_rollup(
                    read_json(args.file), retrieved_on=retrieved)
            elif args.command == "hf-model":
                data = read_json(args.offline_json) if args.offline_json else json_api_get(
                    hf_model_request(args.id))
                prepared = parse_hf_model(data, model_id=args.id,
                                          retrieved_on=retrieved)
            elif args.command == "arena":
                request_url = arena_rows_request(
                    args.config, args.split, offset=args.offset, limit=args.limit)
                data = read_json(args.offline_json) if args.offline_json else json_api_get(
                    request_url)
                prepared = parse_arena_page(
                    data, config=args.config, split=args.split, offset=args.offset,
                    retrieved_on=retrieved)
            elif args.command == "hf-benchmark":
                data = read_json(args.offline_json) if args.offline_json else json_api_get(
                    hf_benchmark_request(args.dataset))
                prepared = parse_hf_benchmark(
                    data, dataset_id=args.dataset, retrieved_on=retrieved)
            else:
                raise CatalogError("unhandled subcommand")

            # Offline files are not authenticated source snapshots. This warning
            # is attached to each extracted observation, preventing accidental
            # interpretation as a verified independently fetched data point.
            if getattr(args, "offline_json", None):
                for record in prepared["observations"]:
                    record["provenance_flags"].append(
                        "offline_supplied_payload_not_authenticated")
                prepared["note"] += "; fixture supplied by caller; NOT authenticated"
            emit(save_snapshot(db, **prepared))
    except (CatalogError, ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"input error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
