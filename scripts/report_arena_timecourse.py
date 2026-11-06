"""Make reproducible Arena retrospective report (MD/CSV/JSON; stdlib only).

No upstream URL lookup is needed: analysis is built from a dated SQLite
snapshot already archived by the data-acquisition workflow.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import argparse
from datetime import date
import csv
import hashlib
import json
from pathlib import Path

from fsl_sources.catalog import connect
from fsl_timecourse.analysis import analyze_series


def create_report(db, output_dir, *, model, config, as_of, category="overall"):
    report = analyze_series(
        db,model_id="arena:"+model, measure=("ips_score" if config.startswith("agent")
                                              else "arena_rating"),
        channel="preference",category=category,
        methodology=("arena-dataset:"+config+":"+
                     ("ips_score" if config.startswith("agent") else "arena_rating")),
        as_of=as_of,mode="retrospective",min_samples=100)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    paths = {
        "json":output_dir/"arena_historical_analysis.json",
        "csv":output_dir/"arena_historical_points.csv",
        "md":output_dir/"arena_historical_report.md",
    }
    paths["json"].write_text(
        json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    fields=("regime","published_on","retrieved_on","value","unit","sample_size",
            "ci_low","ci_high","source_url","snapshot_id")
    with paths["csv"].open("w",encoding="utf-8",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=fields)
        writer.writeheader()
        for era in report["segments"]:
            for point in era["points"]:
                writer.writerow({"regime":era["regime"],**point})
    lines=[
        "# Arena Historical Control | FSL v0.4",
        "",
        f"Model label: `{model}`",
        f"Subset: `{config}`, category: `{category}`",
        f"Retrospective capture cutoff: `{as_of}`",
        "",
        "**Status:** retrospective descriptive series, NOT a historical forecast",
        "",
        "## Methodology-stratified series",
        "",
        "| Published interval | Method regime | Points | Rating/score change | Same-count revisions | Material sample-count drops |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for era in report["segments"]:
        diff=era["level_difference"]
        changed=diff["level_change"] if diff else None
        change="—" if changed is None else f"{changed:+.4f}"
        audit=era["sample_basis_audit"]
        lines.append(
            f"| {era['first_date']} → {era['last_date']} | "
            f"`{era['regime']}` | {era['n_dates']} | {change} | "
            f"{audit['same_reported_count_but_score_changed']} | "
            f"{audit['material_sample_count_drops']} |")
    lines.extend([
        "",
        "## What this can and cannot demonstrate",
        "",
        "A stable public model label can show a changing arena score because the "
        "measurement environment, competitors, weights, sample composition or "
        "scoring algorithm changes. An unchanged published vote count paired "
        "with a changing rating is a useful **measurement negative control**, "
        "not proof of an unchanged underlying ballot set.",
        "",
        "**Do not combine rows across methodology regimes** into an AI capability "
        "multiplier. Do not divide Arena ratings to infer 2–3x intelligence. "
        "This dataset cannot identify any undisclosed model parameter counts.",
        "",
        "Historical leaderboard rows fetched today cannot be used to claim the "
        "same evidence was known when an earlier forecast was issued. "
        "Retrospective fit and genuinely forward issued forecasts are separate.",
        "",
        "Sources:",
        "- https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset",
        "- https://huggingface.co/docs/dataset-viewer/parquet",
        "",
        "See `arena_historical_analysis.json` for source links, 95% rating "
        "interval fields, sample-count anomalies, regime boundaries, and warnings.",
        "",
    ])
    paths["md"].write_text("\n".join(lines),encoding="utf-8")
    return {
        "schema":"fsl/report/0.4","rows":sum(s["n_dates"] for s in report["segments"]),
        "segments":len(report["segments"]),
        "files":{name:{"name":file.name,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()}
                 for name,file in paths.items()},
        "warning":"Historical descriptive measurement, not model-scale/cognitive inference",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--model",required=True)
    p.add_argument("--config",default="text_style_control")
    p.add_argument("--category",default="overall")
    p.add_argument("--as-of",default=date.today().isoformat())
    p.add_argument("--out-dir",default="reports")
    args=p.parse_args()
    with connect(args.db) as db:
        result=create_report(db,args.out_dir,model=args.model,config=args.config,
                             category=args.category,as_of=args.as_of)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
