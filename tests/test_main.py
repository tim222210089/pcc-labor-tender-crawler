import json
import tempfile
import unittest
from pathlib import Path

from src.core import (
    INSTITUTIONAL_FIELDS,
    MARGIN_FIELDS,
    StockCrawlerError,
    merge_monthly_data,
    parse_args,
    roc_to_gregorian,
    write_output,
)
from src.main import run


class MainTests(unittest.TestCase):
    def test_parse_args_builds_default_output_path(self) -> None:
        config = parse_args(["--stock", "2330", "--month", "2026-04"])

        self.assertEqual(config.stock_no, "2330")
        self.assertEqual(config.month, "20260401")
        self.assertEqual(config.output_format, "csv")
        self.assertEqual(
            config.output_path,
            Path("output") / "2330_2026-04_daily.csv",
        )

    def test_roc_to_gregorian(self) -> None:
        self.assertEqual(roc_to_gregorian("115/04/01"), "20260401")

    def test_merge_monthly_data_merges_price_institutional_and_margin(self) -> None:
        payloads = {
            "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20260401&stockNo=2330&response=json": {
                "stat": "OK",
                "title": "demo",
                "fields": ["日期", "成交股數"],
                "data": [["115/04/01", "100"]],
                "notes": [],
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
                "data": [
                    [
                        "2330",
                        "台積電",
                        "11",
                        "12",
                        "-1",
                        "0",
                        "0",
                        "0",
                        "21",
                        "22",
                        "-1",
                        "31",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "29",
                    ]
                ],
            },
            "https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date=20260401&selectType=ALL": {
                "stat": "OK",
                "tables": [
                    {},
                    {
                        "fields": ["代號"],
                        "data": [
                            [
                                "2330",
                                "台積電",
                                "1",
                                "2",
                                "3",
                                "4",
                                "5",
                                "6",
                                "7",
                                "8",
                                "9",
                                "10",
                                "11",
                                "12",
                                "13",
                                "",
                            ]
                        ],
                    },
                ],
            },
        }

        def fake_fetcher(url: str) -> bytes:
            return json.dumps(payloads[url], ensure_ascii=False).encode("utf-8")

        result = merge_monthly_data(
            stock_no="2330",
            month="20260401",
            dataset="daily",
            fetcher=fake_fetcher,
        )

        self.assertEqual(result["fields"][:2], ["日期", "成交股數"])
        self.assertEqual(result["fields"][2:10], INSTITUTIONAL_FIELDS)
        self.assertEqual(result["fields"][10:], MARGIN_FIELDS)
        self.assertEqual(result["rows"][0][0:2], ["115/04/01", "100"])
        self.assertEqual(result["rows"][0][2:10], ["11", "12", "-1", "21", "22", "-1", "31", "29"])
        self.assertEqual(result["rows"][0][10:], ["1", "2", "3", "4", "5", "7", "8", "9", "10", "11"])

    def test_merge_monthly_data_rejects_invalid_json_status(self) -> None:
        def fake_fetcher(_: str) -> bytes:
            return b'{"stat":"NO DATA"}'

        with self.assertRaises(StockCrawlerError):
            merge_monthly_data(
                stock_no="2330",
                month="20260401",
                dataset="daily",
                fetcher=fake_fetcher,
            )

    def test_merge_monthly_data_keeps_row_when_extra_data_is_missing(self) -> None:
        payloads = {
            "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20260401&stockNo=2330&response=json": {
                "stat": "OK",
                "title": "demo",
                "fields": ["日期", "成交股數"],
                "data": [["115/04/09", "100"]],
                "notes": [],
            },
            "https://www.twse.com.tw/fund/T86?response=json&date=20260409&selectType=ALLBUT0999": {
                "stat": "很抱歉，沒有符合條件的資料!",
            },
            "https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date=20260409&selectType=ALL": {
                "stat": "查詢日期小於90年1月1日，請重新查詢!",
            },
        }

        def fake_fetcher(url: str) -> bytes:
            return json.dumps(payloads[url], ensure_ascii=False).encode("utf-8")

        result = merge_monthly_data(
            stock_no="2330",
            month="20260401",
            dataset="daily",
            fetcher=fake_fetcher,
        )

        self.assertEqual(result["rows"][0][0:2], ["115/04/09", "100"])
        self.assertEqual(result["rows"][0][2:], [""] * (len(INSTITUTIONAL_FIELDS) + len(MARGIN_FIELDS)))

    def test_write_output_writes_json(self) -> None:
        result = {
            "stock_no": "2330",
            "month": "20260401",
            "dataset": "daily",
            "title": "demo",
            "fields": ["日期"],
            "rows": [["115/04/01"]],
            "notes": [],
            "extras": {
                "institutional_fields": INSTITUTIONAL_FIELDS,
                "margin_fields": MARGIN_FIELDS,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "data.json"
            write_output(result, target, "json")
            written = json.loads(target.read_text(encoding="utf-8"))

        self.assertEqual(written["股票代號"], "2330")
        self.assertEqual(written["資料"], [["115/04/01"]])

    def test_run_writes_csv_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "data.csv"

            import src.main as main_module

            original_fetch = main_module.fetch_monthly_data
            try:
                main_module.fetch_monthly_data = lambda config: {
                    "stock_no": config.stock_no,
                    "month": config.month,
                    "dataset": config.dataset,
                    "title": "demo",
                    "fields": ["日期", "融資今日餘額"],
                    "rows": [["115/04/01", "100"]],
                    "notes": [],
                    "extras": {
                        "institutional_fields": INSTITUTIONAL_FIELDS,
                        "margin_fields": MARGIN_FIELDS,
                    },
                }
                exit_code = run(
                    [
                        "--stock",
                        "2330",
                        "--month",
                        "2026-04",
                        "--output",
                        str(target),
                    ]
                )
            finally:
                main_module.fetch_monthly_data = original_fetch

            self.assertEqual(exit_code, 0)
            self.assertIn("融資今日餘額", target.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
