"""Read-only bridge from earlier FSL Arena/HF evidence to dated model records.

Distinct measurement channels, methodologies and source eras are NEVER
normalized into one scalar intelligence multiplier. User-provided aliases
must be explicit; exact identities only in source-by-source comparisons.

This module can operate on an existing v0.3/v0.4 observational SQLite
file, but it does not manufacture one or fetch any paid benchmark API.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote
from fsl_sources.catalog import list_observations, iso_day


class MetricsBridgeError(ValueError):pass


def read_observation_panel(db_path, *, source_model_ids, as_of, max_rows=600):
    iso_day(as_of,"as_of")
    if not isinstance(source_model_ids,list) or not source_model_ids:
        raise MetricsBridgeError("explicit source model identities required")
    if len(source_model_ids)>30 or len(set(source_model_ids))!=len(source_model_ids):
        raise MetricsBridgeError("model list must be unique and bounded")
    if not all(isinstance(x,str) and 0<len(x)<180 for x in source_model_ids):
        raise MetricsBridgeError("source model identities must be nonempty")
    if isinstance(max_rows,bool) or not isinstance(max_rows,int) or not 1<=max_rows<=1000:
        raise MetricsBridgeError("row limit must be 1..1000")
    path=Path(db_path).resolve()
    if not path.exists() or not path.is_file():
        raise MetricsBridgeError("existing local SQLite evidence database required")
    # Prefer read-only URI mode; don't create/modify user databases.
    uri="file:"+quote(str(path),safe="/:")+"?mode=ro"
    db=sqlite3.connect(uri,uri=True)
    db.row_factory=sqlite3.Row
    try:
        observations=[]
        for model in source_model_ids:
            observations.extend(list_observations(db,model_id=model,
                                                  limit=max_rows,as_of=as_of))
    except sqlite3.DatabaseError as exc:
        raise MetricsBridgeError("database is not an FSL public observation catalog") from exc
    finally:
        db.close()
    groups={}
    for row in observations:
        published=row["published_on"]
        retrieved=row["retrieved_on"]
        # Missing publisher date is not retroactively converted to a release date.
        if published is not None and published>as_of:
            raise MetricsBridgeError("look-ahead published data leaked")
        if retrieved>as_of:
            raise MetricsBridgeError("future retrieved data leaked")
        key=(row["external_model_id"],row["channel"],row["measure"],
             row["category"],row["methodology"],row["unit"],
             row["source_type"])
        groups.setdefault(key,[]).append(row)
    out=[]
    for key,rows in sorted(groups.items()):
        rows.sort(key=lambda r:(
            r["published_on"] or r["retrieved_on"],r["retrieved_on"],
            r["observation_id"]))
        latest=rows[-1]
        out.append({
            "source_model_id":key[0],"channel":key[1],
            "measure":key[2],"category":key[3],
            "methodology":key[4],"unit":key[5],
            "source_type":key[6],
            "observation_count_in_source_stratum":len(rows),
            "latest_value":latest["value"],
            "latest_published_on":latest["published_on"],
            "latest_retrieved_on":latest["retrieved_on"],
            "latest_source_url":latest["source_url"],
            "latest_sample_size":latest["sample_size"],
            "metric_is_not_G1_to_G4_completion":True,
            "source_method_breaks_not_normalized":True,
        })
    return {
        "schema":"fsl/source-stratified-metrics/0.9",
        "as_of":as_of,
        "source_model_ids":source_model_ids,
        "strata":out,
        "latest_stratum_count":len(out),
        "raw_observation_count":len(observations),
        "cannot_convert_to_task_purchasing_power":True,
        "G1_G2_G3_G4_outcomes_independently_verified":False,
        "warnings":[
            "Arena ratings, benchmarks, self-reports and usage scores are different estimands.",
            "Within-score changes can reflect benchmark methodology changes rather than models.",
            "Historical releases from another source need explicit alias/source version review.",
            "No historical task success/cost is inferred from raw model rating points.",
        ],
    }
