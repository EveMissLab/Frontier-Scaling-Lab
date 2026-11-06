"""Run the AMRAL/FELRA bridge LOCALLY next to a private research workspace.

This tool never sends private source content or runs untrusted verifier code.
The redacted report is written only when explicitly requested and an
out-of-band HMAC key is provided. Never upload the input manifest or private
evidence files to the public FSL repository.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .research_bridge import BridgeError, inspect_private_epoch, public_redacted_summary


def main(argv=None):
    p=argparse.ArgumentParser(description="v0.9 private AMRAL/FELRA research receipt bridge")
    p.add_argument("--manifest",required=True,
                   help="PRIVATE local manifest containing source paths/SHAs")
    p.add_argument("--root",required=True,
                   help="explicit local checkout/evidence directory")
    p.add_argument("--public-output",
                   help="optional REDACTED report path (requires FSL_BRIDGE_EXPORT_KEY)")
    p.add_argument("--private-output",
                   help="optional sensitive local audit path; NEVER commit this")
    args=p.parse_args(argv)
    try:
        manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        now=datetime.now(timezone.utc)
        report=inspect_private_epoch(manifest,root=args.root,
                                     checked_at=now.isoformat())
        if args.private_output:
            dest=Path(args.private_output)
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(report,ensure_ascii=False,indent=2,
                                       sort_keys=True)+"\n",encoding="utf-8")
        key=os.environ.get("FSL_BRIDGE_EXPORT_KEY")
        redacted=public_redacted_summary(report,export_key=key) if (
            args.public_output) else {
                "schema":"fsl/private-receipt-bridge-local-only/0.9",
                "material_count":len(report["material_receipts"]),
                "private_report_saved":bool(args.private_output),
                "public_redacted_report_saved":False,
                "filenames_or_private_research_exposed":False,
                "mathematical_theorem_proved":False,
            }
        if args.public_output:
            now_time=datetime.now(timezone.utc)
            redacted["report_generated_at_utc"]=now_time.isoformat(timespec="seconds")
            redacted["report_generated_at_Asia_Taipei"]=now_time.astimezone(
                ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
            dest=Path(args.public_output)
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(redacted,ensure_ascii=False,indent=2,
                                       sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(redacted,ensure_ascii=False,indent=2,sort_keys=True))
    except (BridgeError,KeyError,TypeError,ValueError,OSError) as exc:
        p.exit(2,"private research bridge error: "+str(exc)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
