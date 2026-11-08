"""FSL v0.20 read-only physical manufacturing quality research CLI.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .audit import ManufacturingStudyError, load_catalog, load_sources, audit


def main(argv=None):
    parser=argparse.ArgumentParser(description="AI physical manufacturing quality; no automatic product certification")
    cmds=parser.add_subparsers(dest="command",required=True)
    cmds.add_parser("catalog")
    cmds.add_parser("sources")
    run=cmds.add_parser("audit")
    run.add_argument("--file",required=True)
    run.add_argument("--as-of",help="ISO 8601 timestamp with timezone or UTC calendar day")
    run.add_argument("--output")
    a=parser.parse_args(argv)
    try:
        if a.command=="catalog":
            cat,ind=load_catalog()
            out={"id":cat["catalog_id"],"version":cat["version"],
                 "axes":len(cat["axes"]),"indicators":len(ind),
                 "real_factory_quality_certified":False}
        elif a.command=="sources":
            evidence=load_sources()
            out={"version":evidence["version"],"sources":len(evidence["sources"]),
                 "scope_limited_published_claims":len(evidence["source_bound_claims"]),
                 "real_factory_quality_certified":False}
        else:
            payload=json.loads(Path(a.file).read_text(encoding="utf-8"))
            out=audit(payload,as_of=a.as_of)
        rendered=json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
        if a.command=="audit" and a.output:
            destination=Path(a.output)
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(rendered,encoding="utf-8")
        else:
            print(rendered,end="")
        return 0
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        parser.exit(2,f"FSL-PMQ audit error: {exc}\n")


if __name__=="__main__":
    raise SystemExit(main())
