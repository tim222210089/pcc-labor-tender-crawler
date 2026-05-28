import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from export_pcc_labor_tenders import (
    AWARDED_HEADERS,
    AwardRecord,
    FAILED_AWARD_HEADERS,
    TenderRecord,
    build_all_page_links,
    extract_title,
    filter_keyword_matches,
    normalize_space,
    parse_award_rows,
    parse_failed_award_reason,
    parse_next_page_links,
    parse_tender_rows,
    parse_winning_vendors,
    resolve_target_date,
    slash_date_string,
    write_workbook,
)


TENDER_ROW_HTML = """
<table id="tpam">
  <tr class="tb_b2">
    <td>1</td>
    <td>臺中市政府運動局</td>
    <td>
      115043001<br>
      <script>var hw = Geps3.CNS.pageCode2Img("臺中市立豐原體育場整修工程委託規劃設計監造技術服務");$("#1").html(hw);</script>
    </td>
    <td>01</td>
    <td>經公開評選或公開徵求之限制性招標</td>
    <td>勞務類</td>
    <td>115/05/04</td>
    <td>115/05/11</td>
    <td>3,450,000</td>
    <td>檢視</td>
  </tr>
</table>
"""

AWARD_ROW_HTML = """
<table id="tpam">
  <tr class="tb_b2">
    <td>1</td>
    <td>僑務委員會</td>
    <td>
      1150010041B<br>
      <script>var hw = Geps3.CNS.pageCode2Img("115年海外僑界急難救助協會『守護海外僑社能量，構築韌性家園』工作研討會");$("#1").html(hw);</script>
    </td>
    <td>公開取得報價單或企劃書</td>
    <td>勞務類</td>
    <td>115/04/30</td>
    <td>1,420,000</td>
    <td>001</td>
    <td></td>
    <td><a href="/prkms/urlSelector/common/atm?pk=NzExOTA2MjE=">檢視</a></td>
  </tr>
</table>
"""

FAILED_AWARD_ROW_HTML = """
<table id="tpam">
  <tr class="tb_b2">
    <td>1</td>
    <td>新北市政府原住民族行政局</td>
    <td>
      1150403<br>
      <script>var hw = Geps3.CNS.pageCode2Img("115年度新北市原住民族部落大學成果展委託專業服務案");$("#1").html(hw);</script>
    </td>
    <td>公開取得報價單或企劃書</td>
    <td>勞務類</td>
    <td>115/04/30</td>
    <td></td>
    <td></td>
    <td>001</td>
    <td><a href="/prkms/urlSelector/common/nonAtm?pk=NzExNzQ0Njc=">檢視</a></td>
  </tr>
</table>
"""

AWARD_DETAIL_HTML = """
<html>
  <body>
    <script>
      $("span[id='spanItem[0].obtain[0].suppName']").html(bidderCnsToImg("第一廠商有限公司"));
      $("span[id='spanItem[0].obtain[1].suppName']").html(bidderCnsToImg("第二廠商有限公司"));
    </script>
  </body>
</html>
"""

FAILED_AWARD_DETAIL_HTML = """
<table>
  <tr>
    <td>無法決標的理由</td>
    <td>流標(無廠商投標或未達法定開標家數)</td>
  </tr>
</table>
"""


class ExportPccLaborTendersTests(unittest.TestCase):
    def test_normalize_space(self) -> None:
        self.assertEqual(normalize_space(" 委託 \n 設計\t監造 "), "委託 設計 監造")

    def test_slash_date_string(self) -> None:
        self.assertEqual(slash_date_string(date(2026, 4, 30)), "2026/04/30")

    def test_resolve_target_date_uses_taipei_date_for_today(self) -> None:
        now = datetime(2026, 5, 6, 22, 45, tzinfo=timezone.utc)
        self.assertEqual(resolve_target_date(None, now), date(2026, 5, 7))

    def test_resolve_target_date_keeps_explicit_date(self) -> None:
        now = datetime(2026, 5, 6, 22, 45, tzinfo=timezone.utc)
        self.assertEqual(resolve_target_date(date(2026, 5, 1), now), date(2026, 5, 1))

    def test_extract_title_from_script(self) -> None:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(TENDER_ROW_HTML, "html.parser")
        title_cell = soup.find_all("td")[2]
        self.assertEqual(
            extract_title(title_cell),
            "臺中市立豐原體育場整修工程委託規劃設計監造技術服務",
        )

    def test_parse_tender_rows(self) -> None:
        rows = parse_tender_rows(TENDER_ROW_HTML)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].agency, "臺中市政府運動局")
        self.assertEqual(rows[0].budget, "3,450,000")
        self.assertEqual(rows[0].procurement_type, "勞務類")

    def test_parse_award_rows(self) -> None:
        rows = parse_award_rows(AWARD_ROW_HTML)
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0],
            AwardRecord(
                "僑務委員會",
                "115年海外僑界急難救助協會『守護海外僑社能量，構築韌性家園』工作研討會",
                "115/04/30",
                "1,420,000",
                "001",
                "",
                detail_url="https://web.pcc.gov.tw/prkms/urlSelector/common/atm?pk=NzExOTA2MjE=",
            ),
        )

    def test_parse_failed_award_rows(self) -> None:
        rows = parse_award_rows(FAILED_AWARD_ROW_HTML)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].agency, "新北市政府原住民族行政局")
        self.assertEqual(rows[0].award_amount, "")
        self.assertEqual(rows[0].award_notice, "")
        self.assertEqual(rows[0].failed_award, "001")
        self.assertEqual(
            rows[0].detail_url,
            "https://web.pcc.gov.tw/prkms/urlSelector/common/nonAtm?pk=NzExNzQ0Njc=",
        )

    def test_parse_winning_vendors_from_detail_script(self) -> None:
        self.assertEqual(parse_winning_vendors(AWARD_DETAIL_HTML), "第一廠商有限公司、第二廠商有限公司")

    def test_parse_winning_vendors_returns_empty_when_missing(self) -> None:
        self.assertEqual(parse_winning_vendors("<html></html>"), "")

    def test_parse_failed_award_reason(self) -> None:
        self.assertEqual(parse_failed_award_reason(FAILED_AWARD_DETAIL_HTML), "流標(無廠商投標或未達法定開標家數)")

    def test_parse_failed_award_reason_returns_empty_when_missing(self) -> None:
        self.assertEqual(parse_failed_award_reason("<table></table>"), "")

    def test_award_record_rows_include_enriched_fields(self) -> None:
        record = AwardRecord(
            "機關",
            "標案",
            "115/05/01",
            "100",
            "001",
            "",
            winning_vendor="得標廠商",
            failed_reason="無法決標理由",
        )

        self.assertEqual(record.as_awarded_row(), ["機關", "標案", "115/05/01", "得標廠商", "100", "001", ""])
        self.assertEqual(record.as_failed_row(), ["機關", "標案", "115/05/01", "無法決標理由", "100", "001", ""])

    def test_write_workbook_includes_award_detail_columns(self) -> None:
        from tempfile import TemporaryDirectory

        from openpyxl import load_workbook

        with TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "out.xlsx"
            write_workbook(
                output,
                [],
                [
                    AwardRecord(
                        "機關",
                        "標案",
                        "115/05/01",
                        "100",
                        "001",
                        "",
                        winning_vendor="得標廠商",
                    )
                ],
                [
                    AwardRecord(
                        "機關",
                        "標案",
                        "115/05/01",
                        "",
                        "",
                        "001",
                        failed_reason="流標",
                    )
                ],
            )

            workbook = load_workbook(output)
            awarded = workbook["keyword_awarded_tenders"]
            failed = workbook["keyword_failed_awards"]
            self.assertEqual([cell.value for cell in awarded[1]], AWARDED_HEADERS)
            self.assertEqual(awarded["D2"].value, "得標廠商")
            self.assertEqual([cell.value for cell in failed[1]], FAILED_AWARD_HEADERS)
            self.assertEqual(failed["D2"].value, "流標")

    def test_parse_next_page_links(self) -> None:
        html = """
        <a href="?tenderType=TENDER_DECLARATION&amp;d-49738-p=2&amp;pageSize=100">2</a>
        <a href="?tenderType=TENDER_DECLARATION&amp;d-49738-p=3&amp;pageSize=100">3</a>
        """
        self.assertEqual(
            parse_next_page_links(html),
            [
                "?tenderType=TENDER_DECLARATION&d-49738-p=2&pageSize=100",
                "?tenderType=TENDER_DECLARATION&d-49738-p=3&pageSize=100",
            ],
        )

    def test_build_all_page_links_from_sparse_pager(self) -> None:
        links = [
            "?tenderType=TENDER_DECLARATION&d-49738-p=2&pageSize=100",
            "?tenderType=TENDER_DECLARATION&d-49738-p=8&pageSize=100",
            "?tenderType=TENDER_DECLARATION&d-49738-p=15&pageSize=100",
        ]
        built = build_all_page_links(links)
        self.assertEqual(len(built), 14)
        self.assertEqual(built[0], "?tenderType=TENDER_DECLARATION&d-49738-p=2&pageSize=100")
        self.assertEqual(built[-1], "?tenderType=TENDER_DECLARATION&d-49738-p=15&pageSize=100")

    def test_filter_keyword_matches(self) -> None:
        rows = [
            TenderRecord("A", "工程委託設計服務", "115/01/01", "115/01/10", "100", "勞務類"),
            TenderRecord("B", "設備採購", "115/01/01", "115/01/10", "200", "勞務類"),
        ]
        matches = filter_keyword_matches(rows, ["委託", "設計"])
        self.assertEqual([row.agency for row in matches], ["A"])

    def test_filter_keyword_matches_excludes_standalone_delegate(self) -> None:
        rows = [
            TenderRecord("A", "工程委託案", "115/01/01", "115/01/10", "100", "勞務類"),
            TenderRecord("B", "委託設計服務案", "115/01/01", "115/01/10", "200", "勞務類"),
            TenderRecord("C", "監造技術服務案", "115/01/01", "115/01/10", "300", "勞務類"),
        ]
        matches = filter_keyword_matches(rows, ["委託", "設計", "監造", "技術服務"])
        self.assertEqual([row.agency for row in matches], ["B", "C"])

    def test_filter_keyword_matches_keeps_delegate_when_it_is_only_keyword(self) -> None:
        rows = [
            TenderRecord("A", "工程委託案", "115/01/01", "115/01/10", "100", "勞務類"),
            TenderRecord("B", "設備採購", "115/01/01", "115/01/10", "200", "勞務類"),
        ]
        matches = filter_keyword_matches(rows, ["委託"])
        self.assertEqual([row.agency for row in matches], ["A"])


if __name__ == "__main__":
    unittest.main()
