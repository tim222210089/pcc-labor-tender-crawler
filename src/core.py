from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StockCrawler/1.2"
TWSE_STOCK_DAY_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
TWSE_STOCK_DAY_AVG_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_AVG"
TWSE_INSTITUTIONAL_URL = "https://www.twse.com.tw/fund/T86"
TWSE_MARGIN_URL = "https://www.twse.com.tw/exchangeReport/MI_MARGN"

INSTITUTIONAL_FIELDS = [
    "外陸資買進股數(不含外資自營商)",
    "外陸資賣出股數(不含外資自營商)",
    "外陸資買賣超股數(不含外資自營商)",
    "投信買進股數",
    "投信賣出股數",
    "投信買賣超股數",
    "自營商買賣超股數",
    "三大法人買賣超股數",
]

MARGIN_FIELDS = [
    "融資買進",
    "融資賣出",
    "融資現金償還",
    "融資前日餘額",
    "融資今日餘額",
    "融券買進",
    "融券賣出",
    "融券現券償還",
    "融券前日餘額",
    "融券今日餘額",
]


class StockCrawlerError(Exception):
    """Raised when the remote stock service returns an invalid response."""


@dataclass(frozen=True)
class FetchConfig:
    stock_no: str
    month: str
    display_month: str
    dataset: str
    output_format: str
    output_path: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="下載台股月資料，並整合同日的三大法人與融資融券資料。"
    )
    parser.add_argument("--stock", required=True, help="股票代碼，例如 2330")
    parser.add_argument(
        "--month",
        required=True,
        help="月份，格式 YYYY-MM，例如 2026-04",
    )
    parser.add_argument(
        "--dataset",
        choices=("daily", "average"),
        default="daily",
        help="daily: 每日成交資訊，average: 每日收盤及月平均價位",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("csv", "json"),
        default="csv",
        help="輸出格式。",
    )
    parser.add_argument(
        "--output",
        help="輸出檔路徑，預設為 ./output/{stock}_{month}_{dataset}.{ext}",
    )
    return parser


def parse_month(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "錯誤的 --month 格式，請使用 YYYY-MM，例如 2026-04。"
        ) from exc

    return parsed.strftime("%Y%m01")


def parse_args(argv: list[str] | None = None) -> FetchConfig:
    args = build_parser().parse_args(argv)
    output_format = args.output_format.lower()

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output") / f"{args.stock}_{args.month}_{args.dataset}.{output_format}"

    return FetchConfig(
        stock_no=args.stock,
        month=parse_month(args.month),
        display_month=args.month,
        dataset=args.dataset,
        output_format=output_format,
        output_path=output_path,
    )


def build_url(base_url: str, params: dict[str, str]) -> str:
    return f"{base_url}?{urlencode(params)}"


def http_get(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except HTTPError as exc:
        raise StockCrawlerError(f"TWSE HTTP 錯誤：{exc.code}") from exc
    except URLError as exc:
        raise StockCrawlerError(f"無法連線到 TWSE：{exc.reason}") from exc


def fetch_json(
    url: str,
    fetcher: Callable[[str], bytes],
    status_keys: tuple[str, ...] = ("stat",),
) -> dict:
    payload = fetcher(url)

    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise StockCrawlerError("TWSE 回傳了無法解析的 JSON。") from exc

    for key in status_keys:
        status = str(data.get(key, "")).strip()
        if status:
            if status.upper() != "OK":
                raise StockCrawlerError(f"TWSE 查詢失敗：{status}")
            break
    else:
        raise StockCrawlerError("TWSE 回應中缺少狀態欄位。")

    return data


def fetch_price_data(
    stock_no: str,
    month: str,
    dataset: str,
    fetcher: Callable[[str], bytes],
) -> dict:
    base_url = TWSE_STOCK_DAY_URL if dataset == "daily" else TWSE_STOCK_DAY_AVG_URL
    data = fetch_json(
        build_url(
            base_url,
            {
                "date": month,
                "stockNo": stock_no,
                "response": "json",
            },
        ),
        fetcher,
    )

    rows = data.get("data")
    fields = data.get("fields")
    if not isinstance(rows, list) or not isinstance(fields, list):
        raise StockCrawlerError("股價資料格式不正確。")

    return {
        "title": data.get("title", ""),
        "fields": fields,
        "rows": rows,
        "notes": data.get("notes", []),
    }


def find_row_by_stock_code(rows: list[list[str]], stock_no: str) -> list[str] | None:
    for row in rows:
        if row and str(row[0]).strip() == stock_no:
            return row
    return None


def fetch_institutional_data(
    stock_no: str,
    date_yyyymmdd: str,
    fetcher: Callable[[str], bytes],
) -> dict[str, str]:
    try:
        data = fetch_json(
            build_url(
                TWSE_INSTITUTIONAL_URL,
                {
                    "response": "json",
                    "date": date_yyyymmdd,
                    "selectType": "ALLBUT0999",
                },
            ),
            fetcher,
        )
    except StockCrawlerError:
        return {}

    fields = data.get("fields")
    rows = data.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise StockCrawlerError("三大法人資料格式不正確。")

    row = find_row_by_stock_code(rows, stock_no)
    if row is None:
        return {}

    record = dict(zip(fields, row))
    return {field: record.get(field, "") for field in INSTITUTIONAL_FIELDS}


def fetch_margin_data(
    stock_no: str,
    date_yyyymmdd: str,
    fetcher: Callable[[str], bytes],
) -> dict[str, str]:
    try:
        data = fetch_json(
            build_url(
                TWSE_MARGIN_URL,
                {
                    "response": "json",
                    "date": date_yyyymmdd,
                    "selectType": "ALL",
                },
            ),
            fetcher,
        )
    except StockCrawlerError:
        return {}

    tables = data.get("tables")
    if not isinstance(tables, list) or len(tables) < 2:
        raise StockCrawlerError("融資融券資料格式不正確。")

    detail_table = tables[1]
    rows = detail_table.get("data")
    if not isinstance(rows, list):
        raise StockCrawlerError("融資融券明細資料格式不正確。")

    row = find_row_by_stock_code(rows, stock_no)
    if row is None:
        return {}

    return {
        "融資買進": row[2],
        "融資賣出": row[3],
        "融資現金償還": row[4],
        "融資前日餘額": row[5],
        "融資今日餘額": row[6],
        "融券買進": row[8],
        "融券賣出": row[9],
        "融券現券償還": row[10],
        "融券前日餘額": row[11],
        "融券今日餘額": row[12],
    }


def roc_to_gregorian(date_text: str) -> str:
    parts = date_text.split("/")
    if len(parts) != 3:
        raise StockCrawlerError(f"無法解析日期：{date_text}")

    roc_year, month, day = (int(part) for part in parts)
    return f"{roc_year + 1911:04d}{month:02d}{day:02d}"


def merge_monthly_data(
    stock_no: str,
    dataset: str,
    month: str,
    fetcher: Callable[[str], bytes] | None = None,
) -> dict:
    fetcher = fetcher or http_get
    price_data = fetch_price_data(stock_no, month, dataset, fetcher)
    merged_fields = price_data["fields"] + INSTITUTIONAL_FIELDS + MARGIN_FIELDS
    merged_rows: list[list[str]] = []

    for price_row in price_data["rows"]:
        date_yyyymmdd = roc_to_gregorian(str(price_row[0]))
        institutional_record = fetch_institutional_data(stock_no, date_yyyymmdd, fetcher)
        margin_record = fetch_margin_data(stock_no, date_yyyymmdd, fetcher)
        merged_rows.append(
            price_row
            + [institutional_record.get(field, "") for field in INSTITUTIONAL_FIELDS]
            + [margin_record.get(field, "") for field in MARGIN_FIELDS]
        )

    return {
        "stock_no": stock_no,
        "month": month,
        "dataset": dataset,
        "title": price_data["title"],
        "fields": merged_fields,
        "rows": merged_rows,
        "notes": price_data["notes"],
        "extras": {
            "institutional_fields": INSTITUTIONAL_FIELDS,
            "margin_fields": MARGIN_FIELDS,
        },
    }


def fetch_monthly_data(
    config: FetchConfig,
    fetcher: Callable[[str], bytes] | None = None,
) -> dict:
    return merge_monthly_data(
        stock_no=config.stock_no,
        dataset=config.dataset,
        month=config.month,
        fetcher=fetcher,
    )


def export_result(result: dict, output_path: Path, output_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "json":
        payload = {
            "股票代號": result["stock_no"],
            "月份": result["month"],
            "資料類型": result["dataset"],
            "標題": result["title"],
            "欄位": result["fields"],
            "資料": result["rows"],
            "附註": result["notes"],
            "額外欄位": result["extras"],
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(result["fields"])
        writer.writerows(result["rows"])


def write_output(result: dict, output_path: Path, output_format: str) -> None:
    export_result(result, output_path, output_format)
