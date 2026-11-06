"""Offline report artifact provenance tests. Apache-2.0."""
import tempfile
from pathlib import Path
import unittest

from fsl_sources.catalog import connect, save_snapshot
from fsl_sources.adapters import parse_arena_page
from scripts.report_arena_timecourse import create_report


class ReportTests(unittest.TestCase):
    def test_report_contains_source_slices_not_capability_multipliers(self):
        with tempfile.TemporaryDirectory() as td:
            db=connect(":memory:")
            try:
                payload={"rows":[
                    {"row_idx":i,"row":{
                        "model_name":"SYNTHETIC-MODEL","rating":1400+i*5,
                        "rating_lower":1395+i*5,"rating_upper":1405+i*5,
                        "category":"overall","vote_count":300,
                        "leaderboard_publish_date":day}}
                    for i,day in enumerate(("2025-08-01","2025-09-01","2025-10-01"))
                ]}
                prepared=parse_arena_page(payload,config="text_style_control",
                                          split="full",offset=0,retrieved_on="2026-11-06")
                save_snapshot(db,**prepared)
                manifest=create_report(db,td,model="SYNTHETIC-MODEL",
                                       config="text_style_control",as_of="2026-11-06")
                self.assertEqual(manifest["rows"],3)
                self.assertEqual(manifest["segments"],1)
                doc=(Path(td)/"arena_historical_report.md").read_text(encoding="utf-8")
                self.assertIn("Same-count revisions",doc)
                self.assertIn("NOT a historical forecast",doc)
                self.assertTrue((Path(td)/"arena_historical_points.csv").exists())
                self.assertEqual(len(manifest["files"]["json"]["sha256"]),64)
            finally:
                db.close()


if __name__=="__main__":
    unittest.main()
