import importlib.util
import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sector-seasonality/fetch_sec_etf_returns.py"
DATA_PATH = ROOT / "frontend/src/data/etf-nport-returns.json"

spec = importlib.util.spec_from_file_location("sec_etf_returns", SCRIPT)
sec_returns = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sec_returns)


class SecEtfReturnTests(unittest.TestCase):
    def test_incremental_fetch_skips_known_and_out_of_window_sec_xml(self):
        entry = next(item for item in sec_returns.SEC_SERIES if item[2] == "AIQ")
        hit = {"_source": {
            "file_type": "NPORT-P", "adsh": "0000000000-26-000001",
            "ciks": ["0001432353"], "file_date": "2026-10-01", "period_ending": "2026-08-31",
        }}
        search = json.dumps({"hits": {"total": {"value": 1, "relation": "eq"}, "hits": [hit]}}).encode()
        with patch.object(sec_returns, "_get", return_value=search) as get:
            result = sec_returns.fetch_series(*entry, existing_accessions={"0000000000-26-000001"})
        self.assertEqual(result["filings"], [])
        self.assertEqual(result["returns"], [])
        self.assertEqual(get.call_count, 1)
        with patch.object(sec_returns, "_get", return_value=search) as get:
            result = sec_returns.fetch_series(*entry, from_period=202606, through_period=202607)
        self.assertEqual(result["filings"], [])
        self.assertEqual(get.call_count, 1)

    def test_nport_month_slots_align_to_report_month(self):
        xml = b'''<edgarSubmission xmlns="urn:sec"><formData><seriesInfo>
          <seriesId>S000018475</seriesId><seriesName>Example Nuclear Fund</seriesName>
          <repPdDate>2026-02-28</repPdDate><classInfo><monthlyTotReturn classId="C000051121"
          rtn1="1.25" rtn2="-2" rtn3="3.5"/></classInfo>
        </seriesInfo></formData></edgarSubmission>'''
        result = sec_returns.parse_filing(xml, "S000018475", "C000051121")
        self.assertEqual([item["period"] for item in result["observations"]], [202512, 202601, 202602])
        self.assertEqual([item["slot"] for item in result["observations"]], ["rtn1", "rtn2", "rtn3"])
        self.assertEqual([item["value"] for item in result["observations"]], [1.25, -2.0, 3.5])
        with self.assertRaisesRegex(ValueError, "series identifier mismatch"):
            sec_returns.parse_filing(xml, "S000000000", "C000051121")
        with self.assertRaisesRegex(ValueError, "lacks reported return"):
            sec_returns.parse_filing(xml, "S000018475", "C000000000")

    def test_published_proxy_history_is_complete_and_filing_linked(self):
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["provider"], "SEC EDGAR public filings")
        self.assertEqual(data["retrievedOn"], "2026-11-01")
        expected = {
            "AIQ": ("2019-09", "2026-08", 84),
            "ROBO": ("2019-08", "2026-07", 84),
            "QTUM": ("2020-01", "2026-06", 78),
            "NLR": ("2019-07", "2026-06", 84),
            "ICLN": ("2019-07", "2026-07", 85),
        }
        self.assertEqual({item["ticker"] for item in data["series"]}, set(expected))
        for item in data["series"]:
            start, end, count = expected[item["ticker"]]
            self.assertEqual((item["periodStart"], item["periodEnd"], len(item["returns"])), (start, end, count))
            periods = [observation["period"] for observation in item["returns"]]
            self.assertEqual(periods, self._periods(periods[0], periods[-1]))
            for observation in item["returns"]:
                self.assertIn(observation["slot"], {"rtn1", "rtn2", "rtn3"})
                self.assertTrue(observation["filingUrl"].startswith("https://www.sec.gov/Archives/edgar/data/"))
                self.assertEqual(len(observation["filingSha256"]), 64)
                self.assertTrue(observation["accession"])
                self.assertTrue(date.fromisoformat(observation["filedOn"]))

    @staticmethod
    def _periods(start, end):
        year, month = divmod(start, 100)
        periods = []
        while year * 100 + month <= end:
            periods.append(year * 100 + month)
            month += 1
            if month == 13:
                year += 1
                month = 1
        return periods


if __name__ == "__main__":
    unittest.main()
