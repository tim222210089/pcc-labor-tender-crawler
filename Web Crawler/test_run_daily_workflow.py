import unittest
from argparse import Namespace
from datetime import date
from pathlib import Path
from unittest.mock import call, patch

from googleapiclient.errors import HttpError
from httplib2 import Response

from run_daily_workflow import (
    DRIVE_RETRY_STATUSES,
    ExportResult,
    UploadResult,
    drive_query_literal,
    execute_drive_request,
    export_excel,
    run,
    upload_to_drive,
)


def http_error(status: int) -> HttpError:
    return HttpError(Response({"status": str(status), "reason": "test"}), b'{"error":"test"}')


class FakeDriveRequest:
    def __init__(self, effects):
        self.effects = list(effects)
        self.execute_count = 0

    def execute(self):
        self.execute_count += 1
        effect = self.effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


class FakeDriveFiles:
    def __init__(self):
        self.create_request = FakeDriveRequest([{"id": "file-1"}])
        self.refresh_request = FakeDriveRequest(
            [{"id": "file-1", "webViewLink": "https://drive/file-1", "webContentLink": "https://drive/download/file-1"}]
        )

    def create(self, **kwargs):
        return self.create_request

    def get(self, **kwargs):
        return self.refresh_request


class FakeDrivePermissions:
    def __init__(self):
        self.create_request = FakeDriveRequest([http_error(503), {"id": "permission-1"}])

    def create(self, **kwargs):
        return self.create_request


class FakeDriveService:
    def __init__(self):
        self.files_resource = FakeDriveFiles()
        self.permissions_resource = FakeDrivePermissions()

    def files(self):
        return self.files_resource

    def permissions(self):
        return self.permissions_resource


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

    def test_execute_drive_request_retries_transient_statuses(self) -> None:
        for status in DRIVE_RETRY_STATUSES:
            with self.subTest(status=status):
                request = FakeDriveRequest([http_error(status), {"ok": True}])
                with patch("run_daily_workflow.time.sleep") as sleep:
                    self.assertEqual(execute_drive_request(request, "test_operation"), {"ok": True})

                self.assertEqual(request.execute_count, 2)
                sleep.assert_called_once_with(2)

    def test_execute_drive_request_does_not_retry_non_transient_status(self) -> None:
        request = FakeDriveRequest([http_error(403)])
        with patch("run_daily_workflow.time.sleep") as sleep:
            with self.assertRaises(HttpError):
                execute_drive_request(request, "test_operation")

        self.assertEqual(request.execute_count, 1)
        sleep.assert_not_called()

    def test_upload_to_drive_retries_transient_permission_failure(self) -> None:
        service = FakeDriveService()
        with (
            patch("run_daily_workflow.build_configured_drive_service", return_value=(service, "owner@example.com")),
            patch("run_daily_workflow.assert_drive_folder_access"),
            patch("googleapiclient.http.MediaFileUpload"),
            patch("run_daily_workflow.time.sleep") as sleep,
        ):
            result = upload_to_drive(Path("out.xlsx"), "folder-id")

        self.assertEqual(
            result,
            UploadResult(
                file_id="file-1",
                web_view_link="https://drive/file-1",
                web_content_link="https://drive/download/file-1",
                created=True,
            ),
        )
        self.assertEqual(service.permissions_resource.create_request.execute_count, 2)
        sleep.assert_called_once_with(2)

    def test_run_does_not_send_line_when_drive_file_already_exists(self) -> None:
        args = Namespace(
            date="today",
            output="out.xlsx",
            keywords="keyword",
            skip_if_drive_file_exists=True,
            send_weekly_summary=False,
        )
        export_result = ExportResult(Path("out.xlsx"), date(2026, 5, 25), 1, 2, 3)
        upload_result = UploadResult("file-1", "https://drive/file-1", "", created=False)
        with (
            patch.dict("run_daily_workflow.os.environ", {"GOOGLE_DRIVE_FOLDER_ID": "folder-id"}),
            patch("run_daily_workflow.export_excel", return_value=export_result),
            patch("run_daily_workflow.upload_to_drive", return_value=upload_result),
            patch("run_daily_workflow.send_line_message") as send_line,
            patch("run_daily_workflow.send_gmail_notification") as send_gmail,
        ):
            self.assertEqual(run(args), 0)

        send_line.assert_not_called()
        send_gmail.assert_not_called()


if __name__ == "__main__":
    unittest.main()
