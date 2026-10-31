import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sector-seasonality/sync_seasonality.py"
INDUSTRY_DATA = ROOT / "frontend/src/data/industry-seasonality.json"

spec = importlib.util.spec_from_file_location("seasonality_sync", SCRIPT)
seasonality_sync = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(seasonality_sync)


class SeasonalitySyncTests(unittest.TestCase):
    def setUp(self):
        self.previous = json.loads(INDUSTRY_DATA.read_text(encoding="utf-8"))

    def test_default_merge_only_fills_new_months(self):
        source_industries = {int(row[0]): row[1:50] for row in self.previous["rows"]}
        source_market = {int(row[0]): row[50] for row in self.previous["rows"]}
        source_industries[202610] = [float(index) for index in range(49)]
        source_market[202610] = 2.5
        source_industries[202611] = [float(index + 1) for index in range(49)]
        source_market[202611] = 3.5
        with patch.object(seasonality_sync, "CURRENT_PERIOD", 202611):
            updated, count = seasonality_sync.merge_industry_dataset(
                self.previous, source_industries, source_market,
                from_period=None, month=None, missing_only=True,
                industry_archive=None, market_archive=None,
                industry_validators={}, market_validators={},
            )
        self.assertEqual(count, 2)
        self.assertEqual(updated["periodEnd"], "2026-11")
        self.assertEqual(updated["rows"][-2][0], 202610)
        self.assertEqual(updated["rows"][-1][-1], 3.5)
        self.assertEqual(updated["rows"][0], self.previous["rows"][0])

    def test_month_filter_does_not_add_another_available_month(self):
        source_industries = {int(row[0]): row[1:50] for row in self.previous["rows"]}
        source_market = {int(row[0]): row[50] for row in self.previous["rows"]}
        for period in (202610, 202611):
            source_industries[period] = [0.0] * 49
            source_market[period] = 1.0
        with patch.object(seasonality_sync, "CURRENT_PERIOD", 202611):
            updated, count = seasonality_sync.merge_industry_dataset(
                self.previous, source_industries, source_market,
                from_period=None, month=202610, missing_only=True,
                industry_archive=None, market_archive=None,
                industry_validators={}, market_validators={},
            )
        self.assertEqual(count, 1)
        self.assertEqual(updated["periodEnd"], "2026-10")

    def test_resync_window_replaces_values_while_missing_only_preserves_them(self):
        old_series = {
            "schemaVersion": 1,
            "provider": "SEC EDGAR public filings",
            "retrievedOn": "2026-01-01",
            "series": [{
                "code": "AI", "periodStart": "2020-01", "periodEnd": "2020-02",
                "historicalFundNames": ["Example Fund"], "filings": [],
                "returns": [
                    {"period": 202001, "value": 1.0, "filedOn": "2020-04-01"},
                    {"period": 202002, "value": 2.0, "filedOn": "2020-04-01"},
                ],
            }],
        }
        # The merger expects all configured series, so use five independent fixture rows.
        old_series["series"] = [copy.deepcopy(old_series["series"][0]) for _ in range(5)]
        for index, item in enumerate(old_series["series"]):
            item["code"] = seasonality_sync.sec_fetcher.SEC_SERIES[index][0]
        fetched = copy.deepcopy(old_series)
        for item in fetched["series"]:
            item["filings"] = [{"accession": "new", "filedOn": "2026-05-01"}]
            item["returns"] = [
                {"period": 202001, "value": 8.0, "filedOn": "2026-05-01"},
                {"period": 202002, "value": 9.0, "filedOn": "2026-05-01"},
            ]
        filled, _ = seasonality_sync.merge_etf_data(old_series, fetched, from_period=202001, month=None, missing_only=True)
        refreshed, _ = seasonality_sync.merge_etf_data(old_series, fetched, from_period=202001, month=None, missing_only=False)
        self.assertEqual(filled["series"][0]["returns"][0]["value"], 1.0)
        self.assertEqual(refreshed["series"][0]["returns"][0]["value"], 8.0)
        self.assertIn("new", {filing["accession"] for filing in refreshed["series"][0]["filings"]})

    def test_conditional_http_304_does_not_download_payload(self):
        response = Mock(status_code=304, headers={})
        response.iter_content.side_effect = AssertionError("304 response must not be read as an archive")
        response.close = Mock()
        with patch.object(seasonality_sync.requests, "get", return_value=response) as get:
            body, headers = seasonality_sync.conditional_download("https://example.test/archive.zip", '"etag-1"', "Tue, 27 Oct 2026 15:18:55 GMT")
        self.assertIsNone(body)
        self.assertEqual(headers, {})
        request_headers = get.call_args.kwargs["headers"]
        self.assertEqual(request_headers["If-None-Match"], '"etag-1"')
        self.assertIn("If-Modified-Since", request_headers)

    def test_month_parser_requires_calendar_format(self):
        self.assertEqual(seasonality_sync.parse_month("2026-10"), 202610)
        with self.assertRaises(Exception):
            seasonality_sync.parse_month("2026-13")


if __name__ == "__main__":
    unittest.main()
