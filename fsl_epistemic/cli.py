"""KIF v0.22 catalog and evidence replay CLI. Apache-2.0."""
import argparse
import json
from pathlib import Path
from .audit import audit, load_catalog, load_json


def main(argv=None):
    p=argparse.ArgumentParser(description="KIF structural evidence audit, not scientific certification")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("catalog")
    a=sub.add_parser("audit")
    a.add_argument("--file",required=True)
    a.add_argument("--as-of",required=True)
    a.add_argument("--mode",default="strict_known_at_time",
                   choices=["strict_known_at_time","retrospective_reconstruction"])
    a.add_argument("--output")
    args=p.parse_args(argv)
    try:
        result=load_catalog() if args.command=="catalog" else audit(load_json(args.file),as_of=args.as_of,mode=args.mode)
        out=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n"
        if args.command=="audit" and args.output:
            dest=Path(args.output)
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(out,encoding="utf-8")
        else:
            print(out,end="")
        return 0
    except (ValueError,TypeError,KeyError,OSError) as exc:
        p.exit(2,f"KIF validation error: {exc}\n")


if __name__=="__main__":
    raise SystemExit(main())
