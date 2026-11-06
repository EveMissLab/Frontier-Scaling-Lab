"""CLI for source-backed measured task time horizons (Apache-2.0)."""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path
from .horizon import HorizonError, compare_matched, horizon_estimate


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser=argparse.ArgumentParser(description="FSL v0.5: controlled H50/H80 (human task minutes)")
    modes=parser.add_subparsers(dest="command",required=True)
    est=modes.add_parser("estimate")
    est.add_argument("--input",required=True)
    pair=modes.add_parser("compare")
    pair.add_argument("--baseline",required=True)
    pair.add_argument("--candidate",required=True)
    for p in (est,pair):
        p.add_argument("--as-of",default=date.today().isoformat())
        p.add_argument("--bootstrap",type=int,default=200)
        p.add_argument("--seed",type=int,default=20261107)
        p.add_argument("--output")
    args=parser.parse_args(argv)
    try:
        from fsl_sources.catalog import iso_day
        cutoff=iso_day(args.as_of,"as_of")
        if args.command=="estimate":
            data=_read(args.input)
            if data["protocol"]["recorded_on"]>cutoff:
                raise HorizonError("would use observations recorded after as-of cutoff")
            result=horizon_estimate(data,bootstrap=args.bootstrap,seed=args.seed)
        else:
            a,b=_read(args.baseline),_read(args.candidate)
            if any(d["protocol"]["recorded_on"]>cutoff for d in (a,b)):
                raise HorizonError("would use observations recorded after as-of cutoff")
            result=compare_matched(a,b,bootstrap=args.bootstrap,seed=args.seed)
        result["as_of"]=cutoff
        output=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,
                          allow_nan=False)+"\n"
        if args.output:
            dest=Path(args.output)
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(output,encoding="utf-8")
        else:
            print(output,end="")
    except (ValueError,KeyError,TypeError,OSError) as exc:
        parser.exit(2,f"measurement error: {exc}\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
