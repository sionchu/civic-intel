"""Offline synthetic tests for research metrics; no source fetch or product fixtures."""

import unittest

from assembly_asset_qa import compact, summarize


class ResearchMetricsTests(unittest.TestCase):
    def test_zero_is_not_missing(self):
        self.assertEqual(compact(0), "0")
        self.assertEqual(compact(None), "")
        self.assertEqual(compact(" \t"), "")
        result = summarize(("test", ["성명", "현재가액"],
                            [{"성명": "synthetic", "현재가액": 0}], 1), {})
        self.assertEqual(result["missing_fields"]["현재가액"], 0)

    def test_ordinals_do_not_hide_duplicate_contents(self):
        rows = [{"성명": "synthetic", "NO": i, "현재가액": 5} for i in [1, 2]]
        result = summarize(("test", list(rows[0]), rows, 1), {})
        self.assertEqual(result["exact_duplicate_excess"], 0)
        self.assertEqual(result["duplicate_excess_excluding_ordinal"], 1)

    def test_crosswalk_requires_exact_code_not_name(self):
        rows = [{"성명": "same synthetic name", "monaCode": code}
                for code in ["CODE1", "CODE2", None]]
        result = summarize(("test", list(rows[0]), rows, 1), {"CODE1": {"HJ1"}})
        self.assertEqual(result["mona_code_in_crosswalk_rows"], 1)
        self.assertEqual(result["mona_codes_absent_from_crosswalk_count"], 1)
        self.assertEqual(result["missing_fields"]["monaCode"], 1)


if __name__ == "__main__":
    unittest.main()
