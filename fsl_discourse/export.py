"""Export source-linked, date-aligned AI public interview claims as UTF-8 CSV.

This exports only original research paraphrases, not transcripts. The source
URL and original Q&A timestamp/section are preserved for human verification.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import json
from .catalog import validate, DiscourseError


HEADERS=[
    "claim_id","speaker_id","organization_at_time","role_at_time",
    "published_on","first_captured_on","interview_recorded_on",
    "publisher","source_id","source_url","transcript_url",
    "timecode","section","source_language","topics",
    "dimensions","modality","claim_scope","paraphrase_zh_tw",
    "reversibility_assessment","annotation_status","evidence_grade",
]


def export_rows(data):
    validate(data)
    src={s["source_id"]:s for s in data["sources"]}
    result=[]
    for c in data["claims"]:
        s=src[c["source_id"]]
        out={
            "claim_id":c["claim_id"],
            "speaker_id":c["speaker_id"],
            "organization_at_time":s["organization_at_time"],
            "role_at_time":s["role_at_time"],
            "published_on":s["published_on"],
            "first_captured_on":s["first_captured_on"],
            "interview_recorded_on":s["interview_recorded_on"] or "",
            "publisher":s["publisher"],
            "source_id":c["source_id"],
            "source_url":s["url"],
            "transcript_url":s["transcript_url"] or "",
            "timecode":c["source_locator"]["timecode"] or "",
            "section":c["source_locator"]["section"] or "",
            "source_language":c["original_language"],
            "topics":";".join(c["topics"]),
            "dimensions":";".join(c["dimensions"]),
            "modality":c["modality"],
            "claim_scope":c["claim_scope"],
            "paraphrase_zh_tw":c["paraphrase_zh_tw"],
            "reversibility_assessment":c["reversibility_assessment"],
            "annotation_status":c["annotation_status"],
            "evidence_grade":s["source_confidence"],
        }
        result.append(out)
    result.sort(key=lambda x:(x["published_on"],x["source_id"],x["claim_id"]))
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description="Original paraphrase export only; no full publisher transcript")
    p.add_argument("--catalog",default="data/agi_asi_public_interviews_seed_2026-11-07.json")
    p.add_argument("--output",required=True)
    args=p.parse_args(argv)
    try:
        data=json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        rows=export_rows(data)
        dest=Path(args.output)
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=HEADERS,extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        print(json.dumps({
            "rows_exported":len(rows),
            "full_copyrighted_transcripts_exported":0,
            "unverified_private_beliefs_exported":0,
            "all_sources_referenced":True,
        },ensure_ascii=False))
    except (OSError,DiscourseError,KeyError,ValueError,TypeError) as exc:
        p.exit(2,"discourse export error: "+str(exc)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
