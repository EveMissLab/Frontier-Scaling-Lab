"""Ensure FSL historical model evidence never merges incompatible benchmarks.

All DB rows below are synthetic; the adapter is compatible with real
v0.3/v0.4 observation stores when supplied as input.
SPDX-License-Identifier: Apache-2.0
"""
import sqlite3
from pathlib import Path
import tempfile
import unittest

from fsl_sources.catalog import connect
from fsl_history.metrics_bridge import read_observation_panel, MetricsBridgeError


class MetricsBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db_path=str(Path(self.tmp.name)/"synthetic_evidence.sqlite")
        with connect(self.db_path) as db:
            db.execute("""INSERT INTO public_snapshots
                (snapshot_id,source_type,resource_id,source_url,published_on,
                 retrieved_on,source_license,attribution,content_sha256)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
                 ("snap0","arena","SYNTHETIC",
                  "https://example.org/SYNTHETIC-FIXTURE",
                  "2024-05-13","2026-11-07","test-not-real","fixture","a"*64))
            sample=[
                ("id1","synthetic-model-A","rating",100,"rating",
                 "preference","old-method","overall","2024-05-13",100),
                ("id2","synthetic-model-A","rating",120,"rating",
                 "preference","new-method","overall","2024-05-13",100),
                ("id3","synthetic-model-A","pass_rate",75,"percent",
                 "benchmark","other-method","unit-tests","2024-05-13",50),
                ("id4","synthetic-model-B","rating",105,"rating",
                 "preference","old-method","overall","2024-05-13",100),
            ]
            for row in sample:
                db.execute("""INSERT INTO public_observations
                    (observation_id,snapshot_id,external_model_id,measure,value,
                     unit,channel,methodology,category,published_on,sample_size,
                     provenance_flags)
                    VALUES(?,'snap0',?,?,?,?,?,?,?,?,?,?)""",
                    (row[0],row[1],row[2],row[3],row[4],row[5],
                     row[6],row[7],row[8],row[9],"synthetic"))
            db.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_readonly_distinct_strata_not_one_intelligence_score(self):
        r=read_observation_panel(self.db_path,
             source_model_ids=["synthetic-model-A","synthetic-model-B"],
             as_of="2026-11-07")
        self.assertEqual(r["raw_observation_count"],4)
        self.assertEqual(r["latest_stratum_count"],4)
        self.assertTrue(r["cannot_convert_to_task_purchasing_power"])
        self.assertFalse(r["G1_G2_G3_G4_outcomes_independently_verified"])
        self.assertEqual(len({(x["methodology"],x["measure"]) for x in
                              r["strata"]}),3)

    def test_no_source_retrieved_2026_in_strict_2024_cutoff(self):
        r=read_observation_panel(self.db_path,
                source_model_ids=["synthetic-model-A"],
                as_of="2024-05-13")
        self.assertEqual(r["raw_observation_count"],0)

    def test_missing_database_does_not_generate_fake_data(self):
        with self.assertRaises(MetricsBridgeError):
            read_observation_panel("/tmp/FSL_NONEXISTENT_DATABASE_17283.sqlite",
                 source_model_ids=["synthetic-model-A"],as_of="2026-11-07")

    def test_no_implicit_fuzzy_aliasing_across_model_ids(self):
        r=read_observation_panel(self.db_path,
                source_model_ids=["synthetic-model-A"],
                as_of="2026-11-07")
        self.assertEqual(r["raw_observation_count"],3)
        self.assertTrue(all(s["source_model_id"]=="synthetic-model-A"
                            for s in r["strata"]))

    def test_no_unbounded_rows_or_duplicate_requested_id(self):
        with self.assertRaises(MetricsBridgeError):
            read_observation_panel(self.db_path,
                 source_model_ids=["a","a"],as_of="2026-11-07")
        with self.assertRaises(MetricsBridgeError):
            read_observation_panel(self.db_path,
                 source_model_ids=["a"],as_of="2026-11-07",max_rows=5000)


if __name__=="__main__":
    unittest.main()
