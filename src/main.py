from __future__ import annotations

import argparse
import sys

from src.core import (
    INSTITUTIONAL_FIELDS,
    MARGIN_FIELDS,
    FetchConfig,
    StockCrawlerError,
    build_parser,
    export_result,
    fetch_institutional_data,
    fetch_margin_data,
    fetch_period_data,
    fetch_price_data,
    find_row_by_stock_code,
    http_get,
    iter_month_keys,
    parse_args,
    parse_month,
    resolve_period_range,
    roc_to_date,
    roc_to_gregorian,
    write_output,
)


def run_cli(argv: list[str] | None = None) -> int:
    try:
        config = parse_args(argv)
        result = fetch_period_data(config)
        write_output(result, config.output_path, config.output_format)
    except (StockCrawlerError, argparse.ArgumentTypeError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1

    print(
        f"已儲存 {config.stock_no} 截至 {config.display_month} 的最近 {config.days} 天 "
        f"{config.dataset} 資料到 {config.output_path.resolve()}"
    )
    return 0


def run(argv: list[str] | None = None) -> int:
    return run_cli(argv)


def main() -> None:
    raise SystemExit(run_cli())


__all__ = [
    "INSTITUTIONAL_FIELDS",
    "MARGIN_FIELDS",
    "FetchConfig",
    "StockCrawlerError",
    "build_parser",
    "export_result",
    "fetch_institutional_data",
    "fetch_margin_data",
    "fetch_period_data",
    "fetch_price_data",
    "find_row_by_stock_code",
    "http_get",
    "iter_month_keys",
    "parse_args",
    "parse_month",
    "resolve_period_range",
    "roc_to_date",
    "roc_to_gregorian",
    "run",
    "run_cli",
    "write_output",
]


if __name__ == "__main__":
    main()
