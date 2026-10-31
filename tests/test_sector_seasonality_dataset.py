import importlib.util
import json
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sector-seasonality/build_dataset.py"
DATA_PATH = ROOT / "frontend/src/data/industry-seasonality.json"

spec = importlib.util.spec_from_file_location("sector_dataset", SCRIPT)
sector_dataset = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sector_dataset)


class IndustrySeasonalityDatasetTests(unittest.TestCase):
    def test_published_panel_is_complete_and_source_pinned(self):
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["schemaVersion"], 3)
        self.assertEqual(data["periodStart"], "1996-01")
        self.assertEqual(data["periodEnd"], "2026-09")
        self.assertEqual(data["completeCalendarYearsThrough"], 2025)
        self.assertEqual(data["latestPartialCalendarYear"], 2026)
        self.assertEqual(data["latestAvailableMonth"], 9)
        self.assertEqual(data["sourceRetrievedOn"], "2026-11-01")
        self.assertEqual(data["marketSourceRetrievedOn"], "2026-11-01")
        self.assertEqual(len(data["industryCodes"]), 49)
        self.assertEqual(len(data["rows"]), 369)
        self.assertEqual([row[0] for row in data["rows"]], list(self._periods()))
        self.assertTrue(all(len(row) == 51 for row in data["rows"]))
        self.assertTrue(all(value != -99.99 and value != -999 for row in data["rows"] for value in row[1:]))
        self.assertEqual(data["industryCodes"], sector_dataset.EXPECTED_INDUSTRIES)
        self.assertEqual(data["sourceArchiveSha256"], "d1a3b0b9896e1e633ed2aa85e24ca144d7998f8ab2ff344e2379383ebeb7b836")
        self.assertEqual(data["marketSourceArchiveSha256"], "b03d39e4bb253dda0f14893db3b78e64b40b8d6549a0fc0fd4111dae84c98618")
        self.assertEqual(data["marketReturnColumn"], 50)
        self.assertIn("Mkt-RF plus RF", data["marketReturnDefinition"])
        self.assertEqual(data["rows"][0][:8], [199601, -1.16, 3.7, -2.53, 3.26, 1.8, 8.17, 3.22])
        self.assertEqual(data["rows"][0][-1], 2.69)
        self.assertEqual(data["rows"][-1][:8], [202609, -8.36, -9.8, -3.84, -8.03, 1.21, -5.75, -12.01])
        self.assertEqual(data["rows"][-1][-1], -0.76)
        self.assertEqual(data["industryCodes"][35:37], ["Softw", "Chips"])
        self.assertIn("value-weighted", data["method"])

    def test_parser_uses_value_weighted_section_not_equal_weighted(self):
        import io
        import zipfile

        headers = sector_dataset.EXPECTED_INDUSTRIES
        lines = ["  Average Value Weighted Returns -- Monthly", "", "," + ",".join(headers)]
        year, month = 1996, 1
        while year < 2026 or (year == 2026 and month <= 9):
            period = year * 100 + month
            values = ["1.25", "-2.50", *(["0.00"] * 47)] if period == 199601 else ["0.00"] * 49
            lines.append(f"{period}," + ",".join(values))
            month += 1
            if month == 13:
                year += 1
                month = 1
        lines.extend(["", "  Average Equal Weighted Returns -- Monthly", "", "," + ",".join(headers)])
        lines.append("199601," + ",".join(["99.00"] * 49))
        lines.append("")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("fixture.csv", "\n".join(lines))
        columns, rows = sector_dataset.read_monthly_value_weighted(buffer.getvalue())
        self.assertEqual(columns, headers)
        self.assertEqual(rows[0], [199601, 1.25, -2.5, *([0.0] * 47)])
        self.assertEqual(rows[-1][0], 202609)

    def test_market_return_is_market_excess_plus_risk_free_and_complete(self):
        import io

        lines = [",Mkt-RF,SMB,HML,RF"]
        year, month = 1996, 1
        while year < 2026 or (year == 2026 and month <= 9):
            period = year * 100 + month
            lines.append(f"{period},1.25,0,0,0.25")
            month += 1
            if month == 13:
                year += 1
                month = 1
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("factors.csv", "\n".join(lines))
        returns = sector_dataset.read_monthly_market_returns(buffer.getvalue())
        self.assertEqual(len(returns), 369)
        self.assertEqual(returns[199601], 1.5)
        self.assertEqual(returns[202609], 1.5)

        missing_month = lines.copy()
        missing_month.pop(2)
        missing_buffer = io.BytesIO()
        with zipfile.ZipFile(missing_buffer, "w") as archive:
            archive.writestr("factors.csv", "\n".join(missing_month))
        with self.assertRaisesRegex(ValueError, "contiguous market months"):
            sector_dataset.read_monthly_market_returns(missing_buffer.getvalue())

        missing_marker = lines.copy()
        missing_marker[1] = "199601,-99.99,0,0,0.25"
        bad_buffer = io.BytesIO()
        with zipfile.ZipFile(bad_buffer, "w") as archive:
            archive.writestr("factors.csv", "\n".join(missing_marker))
        with self.assertRaisesRegex(ValueError, "Missing market-factor marker"):
            sector_dataset.read_monthly_market_returns(bad_buffer.getvalue())

    def test_dynamic_parser_accepts_new_months_after_pinned_release(self):
        import io

        periods = list(self._periods()) + [202610]
        headers = sector_dataset.EXPECTED_INDUSTRIES
        industry_lines = ["  Average Value Weighted Returns -- Monthly", "", "," + ",".join(headers)]
        factor_lines = [",Mkt-RF,SMB,HML,RF"]
        for period in periods:
            industry_lines.append(f"{period}," + ",".join(["1.00"] * 49))
            factor_lines.append(f"{period},1.25,0,0,0.25")
        industry_buffer, factor_buffer = io.BytesIO(), io.BytesIO()
        with zipfile.ZipFile(industry_buffer, "w") as archive:
            archive.writestr("industry.csv", "\n".join(industry_lines))
        with zipfile.ZipFile(factor_buffer, "w") as archive:
            archive.writestr("factors.csv", "\n".join(factor_lines))
        data = sector_dataset.make_dataset(industry_buffer.getvalue(), factor_buffer.getvalue(), end_period=None)
        self.assertEqual(data["periodEnd"], "2026-10")
        self.assertEqual(len(data["rows"]), 370)
        self.assertEqual(data["rows"][-1][-1], 1.5)

    @staticmethod
    def _periods():
        year, month = 1996, 1
        while year < 2026 or (year == 2026 and month <= 9):
            yield year * 100 + month
            month += 1
            if month == 13:
                year += 1
                month = 1


if __name__ == "__main__":
    unittest.main()
