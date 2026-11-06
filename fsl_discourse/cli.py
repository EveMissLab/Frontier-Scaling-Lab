"""FSL v0.10 AI interview source/claim history, as-of and causal caveats.

The host writes only original research annotations and source URLs.
Neither transcript text nor any AI company's private communications are
downloaded or mirrored by this CLI.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .catalog import DiscourseError,validate,asof_view
from .relations import reconcile

DEFAULT_CATALOG="data/agi_asi_public_interviews_seed_2026-11-07.json"
DEFAULT_LINKS="data/discourse_to_model_history_links_v0.10.json"
DEFAULT_MARKET="data/official_ai_history_2024_2026_v0.9.json"


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(result,destination):
    now=datetime.now(timezone.utc)
    result["report_generated_at_utc"]=now.isoformat(timespec="seconds")
    result["report_generated_at_Asia_Taipei"]=now.astimezone(
        ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    result["report_clock_source"]="host clock only, not external notarization"
    raw=json.dumps(result,ensure_ascii=False,indent=2,
                   sort_keys=True,allow_nan=False)+"\n"
    if destination:
        target=Path(destination)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(raw,encoding="utf-8")
    else:
        print(raw,end="")


def _trajectory(catalog,speaker_id,as_of):
    rows=asof_view(catalog,as_of=as_of,mode="retrospective")["rows"]
    filtered=[r for r in rows if r["included"] and r["speaker_id"]==speaker_id]
    speakers={s["speaker_id"] for s in catalog["speakers"]}
    if speaker_id not in speakers:
        raise DiscourseError("unknown speaker")
    if not filtered:
        return {"speaker_id":speaker_id,"claims":[],"observed_change_in_belief":None,
                "chronology_insufficient":True}
    return {
        "speaker_id":speaker_id,
        "as_of":as_of,
        "claims":filtered,
        "source_publication_years":sorted({r["published_on"][:4] for r in filtered}),
        "public_utterance_history_observed":True,
        "observed_change_in_private_belief":None,
        "observed_independent_causal_effect":None,
        "observed_organizational_reversal":None,
        "annotation":"Chronological descriptions; do not infer private change, hypocrisy, or AGI truth from rhetoric.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(
        description="Dated AI public interview self-conceptions, intent and open reversibility research")
    p.add_argument("--catalog",default=DEFAULT_CATALOG)
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("validate")
    a.add_argument("--output")
    t=sub.add_parser("asof")
    t.add_argument("--as-of",required=True)
    t.add_argument("--mode",default="retrospective",
                   choices=["retrospective","strict_known_at_time"])
    t.add_argument("--output")
    s=sub.add_parser("speaker")
    s.add_argument("--speaker-id",required=True)
    s.add_argument("--as-of",required=True)
    s.add_argument("--output")
    l=sub.add_parser("links")
    l.add_argument("--market",default=DEFAULT_MARKET)
    l.add_argument("--relations",default=DEFAULT_LINKS)
    l.add_argument("--as-of",required=True)
    l.add_argument("--output")
    args=p.parse_args(argv)
    try:
        data=_read(args.catalog)
        if args.command=="validate":
            result=validate(data)
        elif args.command=="asof":
            result=asof_view(data,as_of=args.as_of,mode=args.mode)
        elif args.command=="speaker":
            validate(data)
            result=_trajectory(data,args.speaker_id,args.as_of)
        else:
            result=reconcile(data,_read(args.market),_read(args.relations),
                             as_of=args.as_of)
        _write(result,getattr(args,"output",None))
    except (DiscourseError,ValueError,TypeError,KeyError,OSError) as exc:
        p.exit(2,"discourse research error: "+str(exc)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
