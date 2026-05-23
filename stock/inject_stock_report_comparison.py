import argparse
import csv
import html
import json
import re
from pathlib import Path


def load_report(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(r"const R = (\{.*?\});", text, re.S)
    if not match:
        raise ValueError(f"Cannot find report JSON in {path}")
    return json.loads(match.group(1))


def save_snapshot(report_path: Path, output_path: Path) -> None:
    report = load_report(report_path)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def number(value):
    try:
        if value is None or value == "":
            return None
        cleaned = re.sub(r"[^0-9.\-]", "", str(value))
        if cleaned in ("", "-", ".", "-."):
            return None
        return float(cleaned)
    except ValueError:
        return None


def fmt(value, digits=2):
    n = number(value)
    if n is None:
        return "NA"
    if abs(n - round(n)) < 0.000001:
        return f"{int(round(n)):,}"
    return f"{n:,.{digits}f}"


def pct_change(old, new):
    old_n = number(old)
    new_n = number(new)
    if old_n in (None, 0) or new_n is None:
        return "NA"
    pct = (new_n - old_n) / old_n * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def get_chart_series(report: dict, *names):
    chart = report.get("chart") or {}
    for name in names:
        values = chart.get(name)
        if isinstance(values, list):
            return values
    return []


def last5_sum(report: dict, *names):
    values = [number(v) for v in get_chart_series(report, *names)]
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values[-5:])


def direction(value):
    n = number(value)
    if n is None:
        return "NA"
    if n > 0:
        return f"買超 {fmt(n)}"
    if n < 0:
        return f"賣超 {fmt(abs(n))}"
    return "持平"


def csv_latest(csv_path: Path) -> dict:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    latest = rows[-1]
    return {
        "date": latest.get("日期") or latest.get("date"),
        "close": latest.get("收盤價") or latest.get("close"),
        "margin": latest.get("融資餘額") or latest.get("margin"),
        "foreign": latest.get("外資買賣超") or latest.get("foreign"),
        "trust": latest.get("投信買賣超") or latest.get("trust"),
        "rows": len(rows),
    }


def pick(report: dict, *names):
    for name in names:
        if name in report and report[name] not in (None, ""):
            return report[name]
    return "NA"


def support_summary(report: dict):
    levels = report.get("support_levels") or report.get("supports") or []
    if isinstance(levels, list) and levels:
        parts = []
        for item in levels[:3]:
            if isinstance(item, dict):
                parts.append(str(item.get("price") or item.get("level") or item.get("value") or item))
            else:
                parts.append(str(item))
        return " / ".join(parts)
    return pick(report, "support_summary", "support_desc")


def broker_summary(report: dict):
    targets = report.get("broker_targets") or {}
    if not isinstance(targets, dict):
        return "NA"
    avg = targets.get("average_target") or targets.get("average")
    high = targets.get("highest_target") or targets.get("highest")
    low = targets.get("lowest_target") or targets.get("lowest")
    bias = targets.get("bias") or ""
    values = []
    if avg is not None:
        values.append(f"均價 {fmt(avg)}")
    if high is not None:
        values.append(f"高 {fmt(high)}")
    if low is not None:
        values.append(f"低 {fmt(low)}")
    if bias:
        values.append(str(bias))
    return "，".join(values) if values else "NA"


def build_comparison(symbol: str, code: str, old_report: dict, new_report: dict, new_csv: Path) -> dict:
    latest = csv_latest(new_csv)
    old_close = old_report.get("latest_close")
    new_close = new_report.get("latest_close")
    old_margin = old_report.get("margin_balance") or old_report.get("latest_margin")
    new_margin = latest.get("margin") or new_report.get("margin_balance") or new_report.get("latest_margin")
    margin_note = "正常解讀"
    if number(new_margin) == 0:
        margin_note = "資料品質警訊：最新融資餘額為 0.0，不作融資歸零結論"
    rows = [
        {"item": "報告日期", "previous": str(old_report.get("as_of", "NA")), "current": str(new_report.get("as_of", latest.get("date", "NA"))), "change": "資料已更新"},
        {"item": "最新收盤價", "previous": fmt(old_close), "current": fmt(new_close), "change": pct_change(old_close, new_close)},
        {"item": "趨勢評級", "previous": str(old_report.get("rating", "NA")), "current": str(new_report.get("rating", "NA")), "change": "維持" if old_report.get("rating") == new_report.get("rating") else "改變"},
        {"item": "主要支撐/壓力", "previous": str(support_summary(old_report)), "current": str(support_summary(new_report)), "change": "依新價格結構重估"},
        {"item": "週線與週 KD", "previous": str(pick(old_report, "weekly_signal", "weekly_bias", "weekly_kd_signal")), "current": str(pick(new_report, "weekly_signal", "weekly_bias", "weekly_kd_signal")), "change": "依最新週線資料重估"},
        {"item": "外資近 5 日方向", "previous": direction(last5_sum(old_report, "foreign", "foreign_flow", "foreign_net")), "current": direction(last5_sum(new_report, "foreign", "foreign_flow", "foreign_net")), "change": "觀察是否由買轉賣或賣壓收斂"},
        {"item": "投信近 5 日方向", "previous": direction(last5_sum(old_report, "trust", "trust_flow", "trust_net")), "current": direction(last5_sum(new_report, "trust", "trust_flow", "trust_net")), "change": "觀察是否延續作帳或調節"},
        {"item": "融資水位", "previous": fmt(old_margin), "current": fmt(new_margin), "change": margin_note},
        {"item": "目標價共識", "previous": broker_summary(old_report), "current": broker_summary(new_report), "change": "依最新可追溯來源更新"},
        {"item": "消息面判斷", "previous": str(old_report.get("news_bias", "NA")), "current": str(new_report.get("news_bias", "NA")), "change": "納入最新新聞與目標價"},
    ]
    return {
        "symbol": symbol,
        "code": code,
        "previous_as_of": old_report.get("as_of"),
        "current_as_of": new_report.get("as_of") or latest.get("date"),
        "latest_csv": latest,
        "rows": rows,
        "summary": f"{symbol}({code}) 本次報告由 {old_report.get('as_of', '上次')} 更新至 {new_report.get('as_of', latest.get('date', '本次'))}，收盤價變化 {pct_change(old_close, new_close)}；支撐、加碼與週線策略已按最新 90 日資料重估。",
    }


def comparison_html(comparison: dict) -> str:
    rows = []
    for row in comparison["rows"]:
        cells = "".join(f"<td>{html.escape(str(row[key]))}</td>" for key in ("item", "previous", "current", "change"))
        rows.append(f"<tr>{cells}</tr>")
    return (
        '<div class="section-title">與上次報告比對</div>'
        '<div class="notice">'
        f"{html.escape(comparison['summary'])}"
        "</div>"
        '<div class="table-wrap"><table>'
        "<thead><tr><th>項目</th><th>上次報告</th><th>本次報告</th><th>變化/解讀</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )


def inject(html_path: Path, comparison: dict) -> None:
    text = html_path.read_text(encoding="utf-8")
    block = comparison_html(comparison)
    marker = '<div class="panel" id="p5">'
    if "與上次報告比對" in text:
        text = re.sub(
            r'<div class="section-title">與上次報告比對</div>.*?(?=<div class="notice">本報告為技術分析教育用途)',
            block,
            text,
            count=1,
            flags=re.S,
        )
        html_path.write_text(text, encoding="utf-8")
        return
    if marker in text:
        text = text.replace(marker, marker + block, 1)
    else:
        text = text.replace("</body>", block + "</body>", 1)
    html_path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--report", required=True)
    s.add_argument("--output", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--symbol", required=True)
    c.add_argument("--code", required=True)
    c.add_argument("--previous", required=True)
    c.add_argument("--current-report", required=True)
    c.add_argument("--current-csv", required=True)
    c.add_argument("--comparison-output", required=True)
    c.add_argument("--inject-html", required=True)
    args = parser.parse_args()
    if args.cmd == "snapshot":
        save_snapshot(Path(args.report), Path(args.output))
        return
    old_report = json.loads(Path(args.previous).read_text(encoding="utf-8-sig"))
    new_report = load_report(Path(args.current_report))
    comparison = build_comparison(args.symbol, args.code, old_report, new_report, Path(args.current_csv))
    Path(args.comparison_output).write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    inject(Path(args.inject_html), comparison)


if __name__ == "__main__":
    main()
