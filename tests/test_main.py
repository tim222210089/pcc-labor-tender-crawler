import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.core import (
    INSTITUTIONAL_FIELDS,
    MARGIN_FIELDS,
    StockCrawlerError,
    iter_month_keys,
    merge_period_data,
    parse_args,
    resolve_period_range,
    roc_to_gregorian,
    write_output,
)
from src.main import run


class MainTests(unittest.TestCase):
    def test_parse_args_builds_default_output_path(self) -> None:
        config = parse_args(["--stock", "2330", "--month", "2026-04", "--days", "90"])

        self.assertEqual(config.stock_no, "2330")
        self.assertEqual(config.month, "20260401")
        self.assertEqual(config.days, 90)
        self.assertEqual(config.output_format, "csv")
        self.assertEqual(
            config.output_path,
            Path("output") / "2330_2026-04_90d_daily.csv",
        )

    def test_roc_to_gregorian(self) -> None:
        self.assertEqual(roc_to_gregorian("115/04/01"), "20260401")

    def test_resolve_period_range_for_current_month(self) -> None:
        start_date, end_date = resolve_period_range(
            "2026-04",
            30,
            today=date(2026, 4, 27),
        )

        self.assertEqual(start_date.isoformat(), "2026-03-29")
        self.assertEqual(end_date.isoformat(), "2026-04-27")

    def test_iter_month_keys_spans_multiple_months(self) -> None:
        keys = iter_month_keys(date(2026, 3, 29), date(2026, 5, 2))
        self.assertEqual(keys, ["20260301", "20260401", "20260501"])

    def test_merge_period_data_merges_and_filters_cross_month_rows(self) -> None:
        payloads = {
            "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20260301&stockNo=2330&response=json": {
                "stat": "OK",
                "title": "march",
                "fields": ["日期", "成交股數"],
                "data": [["115/03/28", "90"], ["115/03/29", "100"]],
                "notes": [],
            },
            "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20260401&stockNo=2330&response=json": {
                "stat": "OK",
                "title": "april",
                "fields": ["日期", "成交股數"],
                "data": [["115/04/01", "110"], ["115/04/28", "999"]],
                "notes": [],
            },
            "https://www.twse.com.tw/fund/T86?response=json&date=20260329&selectType=ALLBUT0999": {
                "stat": "OK",
                "fields": [
                    "證券代號",
                    "證券名稱",
                    "外陸資買進股數(不含外資自營商)",
                    "外陸資賣出股數(不含外資自營商)",
                    "外陸資買賣超股數(不含外資自營商)",
                    "外資自營商買進股數",
                    "外資自營商賣出股數",
                    "外資自營商買賣超股數",
                    "投信買進股數",
                    "投信賣出股數",
                    "投信買賣超股數",
                    "自營商買賣超股數",
                    "自營商買進股數(自行買賣)",
                    "自營商賣出股數(自行買賣)",
                    "自營商買賣超股數(自行買賣)",
                    "自營商買進股數(避險)",
                    "自營商賣出股數(避險)",
                    "自營商買賣超股數(避險)",
                    "三大法人買賣超股數",
                ],
                "data": [["2330", "台積電", "11", "12", "-1", "0", "0", "0", "21", "22", "-1", "31", "0", "0", "0", "0", "0", "0", "29"]],
            },
            "https://www.twse.com.tw/fund/T86?response=json&date=20260401&selectType=ALLBUT0999": {
                "stat": "OK",
                "fields": [
                    "證券代號",
                    "證券名稱",
                    "外陸資買進股數(不含外資自營商)",
                    "外陸資賣出股數(不含外資自營商)",
                    "外陸資買賣超股數(不含外資自營商)",
                    "外資自營商買進股數",
                    "外資自營商賣出股數",
                    "外資自營商買賣超股數",
                    "投信買進股數",
                    "投信賣出股數",
                    "投信買賣超股數",
                    "自營商買賣超股數",
                    "自營商買進股數(自行買賣)",
                    "自營商賣出股數(自行買賣)",
                    "自營商買賣超股數(自行買賣)",
                    "自營商買進股數(避險)",
                    "自營商賣出股數(避險)",
                    "自營商買賣超股數(避險)",
                    "三大法人買賣超股數",
                ],
                "data": [["2330", "台積電", "51", "52", "-1", "0", "0", "0", "61", "62", "-1", "71", "0", "0", "0", "0", "0", "0", "79"]],
            },
            "https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date=20260329&selectType=ALL": {
                "stat": "OK",
                "tables": [{}, {"data": [["2330", "台積電", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", ""]]}],
            },
            "https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date=20260401&selectType=ALL": {
                "stat": "OK",
                "tables": [{}, {"data": [["2330", "台積電", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", ""]]}],
            },
        }

        def fake_fetcher(url: str) -> bytes:
            return json.dumps(payloads[url], ensure_ascii=False).encode("utf-8")

        result = merge_period_data(
            stock_no="2330",
            dataset="daily",
            display_month="2026-04",
            days=30,
            fetcher=fake_fetcher,
            today=date(2026, 4, 27),
        )

        self.assertEqual(result["days"], 30)
        self.assertEqual(result["fields"][:2], ["日期", "成交股數"])
        self.assertEqual([row[0] for row in result["rows"]], ["115/03/29", "115/04/01"])
        self.assertEqual(result["rows"][0][2:10], ["11", "12", "-1", "21", "22", "-1", "31", "29"])
        self.assertEqual(result["rows"][1][10:], ["21", "22", "23", "24", "25", "27", "28", "29", "30", "31"])

    def test_merge_period_data_rejects_invalid_json_status(self) -> None:
        def fake_fetcher(_: str) -> bytes:
            return b'{"stat":"NO DATA"}'

        with self.assertRaises(StockCrawlerError):
            merge_period_data(
                stock_no="2330",
                dataset="daily",
                display_month="2026-04",
                days=30,
                fetcher=fake_fetcher,
                today=date(2026, 4, 27),
            )

    def test_write_output_writes_json(self) -> None:
        result = {
            "stock_no": "2330",
            "month": "2026-04",
            "days": 90,
            "dataset": "daily",
            "title": "demo",
            "fields": ["日期"],
            "rows": [["115/04/01"]],
            "notes": [],
            "extras": {
                "institutional_fields": INSTITUTIONAL_FIELDS,
                "margin_fields": MARGIN_FIELDS,
                "start_date": "2026-01-28",
                "end_date": "2026-04-27",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "data.json"
            write_output(result, target, "json")
            written = json.loads(target.read_text(encoding="utf-8"))

        self.assertEqual(written["期間天數"], 90)
        self.assertEqual(written["資料"], [["115/04/01"]])

    def test_run_writes_csv_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "data.csv"

            import src.main as main_module

            original_fetch = main_module.fetch_period_data
            try:
                main_module.fetch_period_data = lambda config: {
                    "stock_no": config.stock_no,
                    "month": config.display_month,
                    "days": config.days,
                    "dataset": config.dataset,
                    "title": "demo",
                    "fields": ["日期", "融資今日餘額"],
                    "rows": [["115/04/01", "100"]],
                    "notes": [],
                    "extras": {
                        "institutional_fields": INSTITUTIONAL_FIELDS,
                        "margin_fields": MARGIN_FIELDS,
                        "start_date": "2026-01-28",
                        "end_date": "2026-04-27",
                    },
                }
                exit_code = run(
                    [
                        "--stock",
                        "2330",
                        "--month",
                        "2026-04",
                        "--days",
                        "90",
                        "--output",
                        str(target),
                    ]
                )
            finally:
                main_module.fetch_period_data = original_fetch

            self.assertEqual(exit_code, 0)
            self.assertIn("融資今日餘額", target.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
