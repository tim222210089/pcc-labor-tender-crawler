import unittest
from datetime import date
from pathlib import Path
from unittest.mock import call, patch

from run_daily_workflow import ExportResult, drive_query_literal, export_excel


class RunDailyWorkflowTests(unittest.TestCase):
    def test_drive_query_literal_escapes_quotes_and_backslashes(self) -> None:
        self.assertEqual(drive_query_literal(r"folder\id's"), r"folder\\id\'s")

    def test_export_excel_uses_is_now_for_today_tenders_and_taipei_date_for_awards(self) -> None:
        with (
            patch("run_daily_workflow.resolve_target_date", return_value=date(2026, 5, 8)),
            patch("run_daily_workflow.fetch_all_records", return_value=[]) as fetch_all,
            patch("run_daily_workflow.filter_labor_records", return_value=[]),
            patch("run_daily_workflow.filter_keyword_matches", return_value=[]),
            patch("run_daily_workflow.fetch_award_records", return_value=[]) as fetch_awards,
            patch("run_daily_workflow.write_workbook") as write_workbook,
        ):
            result = export_excel("today", Path("out.xlsx"), "委託")

        self.assertEqual(result, ExportResult(Path("out.xlsx"), date(2026, 5, 8), 0, 0, 0))
        fetch_all.assert_called_once_with(None)
        self.assertEqual(
            fetch_awards.call_args_list,
            [
                call(date(2026, 5, 8), "TENDER_STATUS_1"),
                call(date(2026, 5, 8), "TENDER_STATUS_2"),
            ],
        )
        write_workbook.assert_called_once()


if __name__ == "__main__":
    unittest.main()
