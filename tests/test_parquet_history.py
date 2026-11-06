"""Offline Parquet provenance tests, no DuckDB or external network required.

SPDX-License-Identifier: Apache-2.0
"""
import unittest
from pathlib import Path
from fsl_sources.catalog import CatalogError, connect
from fsl_timecourse.parquet_history import choose_parquet, parquet_history
from fsl_timecourse.analysis import analyze_series


PARQUET_URL=("https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/"
             "resolve/refs%2Fconvert%2Fparquet/text_style_control/full/0000.parquet")


def fake_index(config="text_style_control", size=4096):
    return {"partial":False, "parquet_files":[
        {"config":config, "split":"full", "url":PARQUET_URL,
         "size":size, "filename":"0000.parquet"}]}


def record(day, score):
    return {"model_name":"gpt-4o-2024-05-13","category":"overall",
            "leaderboard_publish_date":day,"rating":score,
            "rating_lower":score-5,"rating_upper":score+5,"vote_count":400}


class ParquetTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_file_selection_filters_exact_split(self):
        self.assertEqual(len(choose_parquet(fake_index(),
                         config="text_style_control")), 1)
        with self.assertRaises(CatalogError):
            choose_parquet(fake_index(), config="agent")
        with self.assertRaises(CatalogError):
            choose_parquet(fake_index(size=150*1024*1024),
                           config="text_style_control")
        with self.assertRaises(CatalogError):
            choose_parquet(dict(fake_index(), partial=True),
                           config="text_style_control")

    def test_historical_parquet_projection_is_retrospective_only(self):
        def download(url, path, size):
            self.assertEqual(url, PARQUET_URL)
            Path(path).write_bytes(b"SYNTHETIC NOT REAL PARQUET")
            return {"sha256":"a"*64,"downloaded_bytes":26}
        def query(paths, config, model, category, max_rows):
            self.assertEqual(model,"gpt-4o-2024-05-13")
            self.assertEqual(len(paths),1)
            return [record("2025-08-01",1400),
                    record("2025-09-01",1410),
                    record("2025-10-01",1420)], False
        result = parquet_history(
            self.db,config="text_style_control",model="gpt-4o-2024-05-13",
            retrieved_on="2026-11-06",download=download,query=query,
            fetch_index=lambda _:fake_index())
        self.assertEqual(result["rows_stored"],3)
        self.assertEqual(result["status"],"historical_retrospective")
        self.assertEqual(len(result["parquet_files"]),1)
        args=dict(model_id="arena:gpt-4o-2024-05-13",
                  channel="preference",measure="arena_rating",
                  category="overall",
                  methodology="arena-dataset:text_style_control:arena_rating")
        strict=analyze_series(self.db,as_of="2025-10-31",
                              mode="strict_asof",**args)
        retrospective=analyze_series(self.db,as_of="2025-10-31",
                                     mode="retrospective",**args)
        self.assertEqual(strict["unique_published_dates"],0)
        self.assertEqual(retrospective["unique_published_dates"],3)

    def test_parquet_conflicting_same_day_records_refused(self):
        def download(url, path, size):
            Path(path).write_bytes(b"x")
            return {"sha256":"b"*64,"downloaded_bytes":1}
        def query(*args, **kw):
            return [record("2025-09-01",1400),record("2025-09-01",1500)],False
        with self.assertRaises(CatalogError):
            parquet_history(
                self.db,config="text_style_control",model="gpt-4o-2024-05-13",
                retrieved_on="2026-11-06",download=download,query=query,
                fetch_index=lambda _:fake_index())
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM public_snapshots").fetchone()[0],0)


if __name__=="__main__":
    unittest.main()
