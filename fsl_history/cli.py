"""Public historical release/price timelines; explicit as-of and dated exports."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import csv
import io
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .catalog import CatalogError, validate, timeline, period_matrix
from .metrics_bridge import read_observation_panel, MetricsBridgeError

DEFAULT="data/official_ai_history_2024_2026_v0.9.json"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _output(result,output,kind):
    now=datetime.now(timezone.utc)
    result["report_generated_at_utc"]=now.isoformat(timespec="seconds")
    result["report_generated_at_Asia_Taipei"]=now.astimezone(
        ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    result["time_source"]="host system clock; not independent trusted time attestation"
    raw=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True,
                   allow_nan=False)+"\n"
    if output:
        target=Path(output)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(raw,encoding="utf-8")
    else:
        print(raw,end="")


def main(argv=None):
    p=argparse.ArgumentParser(description="FSL v0.9 official market timeline; not a model task benchmark")
    p.add_argument("--catalog",default=DEFAULT)
    sub=p.add_subparsers(dest="action",required=True)
    check=sub.add_parser("validate"); check.add_argument("--output")
    tl=sub.add_parser("timeline")
    tl.add_argument("--as-of",required=True)
    tl.add_argument("--mode",choices=["retrospective","strict_known_at_time"],
                    default="retrospective")
    tl.add_argument("--output")
    matrix=sub.add_parser("matrix")
    matrix.add_argument("--month-ends",required=True,
                        help="semicolon-separated YYYY-MM-DD explicit cutoff dates")
    matrix.add_argument("--output")
    metrics=sub.add_parser("metrics")
    metrics.add_argument("--db",required=True,help="v0.3/0.4 evidence database (read-only)")
    metrics.add_argument("--model",action="append",required=True,
                         help="exact source model ID; repeat for multiple models")
    metrics.add_argument("--as-of",required=True)
    metrics.add_argument("--output")
    args=p.parse_args(argv)
    try:
        data=_read(args.catalog) if args.action!="metrics" else None
        if args.action=="validate":
            result=validate(data)
        elif args.action=="timeline":
            result=timeline(data,as_of=args.as_of,mode=args.mode)
        elif args.action=="metrics":
            result=read_observation_panel(args.db,source_model_ids=args.model,
                                          as_of=args.as_of)
        else:
            result=period_matrix(data,month_ends=args.month_ends.split(";"))
        _output(result,getattr(args,"output",None),args.action)
    except (CatalogError,MetricsBridgeError,ValueError,KeyError,TypeError,OSError) as exc:
        p.exit(2,"historical catalog error: "+str(exc)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
