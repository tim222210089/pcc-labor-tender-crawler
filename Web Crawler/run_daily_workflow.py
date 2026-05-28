from __future__ import annotations

import argparse
import base64
import json
import os
import smtplib
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

from export_pcc_labor_tenders import (
    enrich_awarded_records_with_vendors,
    enrich_failed_awards_with_reasons,
    fetch_all_records,
    fetch_award_records,
    filter_keyword_matches,
    filter_labor_records,
    parse_cli_date,
    parse_keywords,
    resolve_target_date,
    write_workbook,
)


DRIVE_FILE_FIELDS = "id,name,webViewLink,webContentLink"
EXCEL_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DRIVE_RETRY_STATUSES = {429, 500, 502, 503, 504}
DRIVE_RETRY_DELAYS_SECONDS = [2, 5, 10, 20, 30]


@dataclass(frozen=True)
class ExportResult:
    output_path: Path
    target_date: date
    keyword_matches: int
    keyword_awarded_tenders: int
    keyword_failed_awards: int


@dataclass(frozen=True)
class UploadResult:
    file_id: str
    web_view_link: str
    web_content_link: str
    created: bool


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_json_env(name: str) -> dict[str, Any]:
    raw = get_required_env(name)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must be valid JSON") from exc


def export_excel(raw_date: str, output_path: Path, keywords_raw: str) -> ExportResult:
    _, explicit_date = parse_cli_date(raw_date)
    keywords = parse_keywords(keywords_raw)
    target_date = resolve_target_date(explicit_date)

    records = fetch_all_records(explicit_date)
    labor_records = filter_labor_records(records)
    keyword_records = filter_keyword_matches(labor_records, keywords)
    awarded_rows = fetch_award_records(target_date, "TENDER_STATUS_1")
    failed_rows = fetch_award_records(target_date, "TENDER_STATUS_2")
    keyword_awarded_rows = filter_keyword_matches(awarded_rows, keywords)
    keyword_failed_rows = filter_keyword_matches(failed_rows, keywords)
    keyword_awarded_rows = enrich_awarded_records_with_vendors(keyword_awarded_rows)
    keyword_failed_rows = enrich_failed_awards_with_reasons(keyword_failed_rows)
    write_workbook(output_path, keyword_records, keyword_awarded_rows, keyword_failed_rows)

    return ExportResult(
        output_path=output_path,
        target_date=target_date,
        keyword_matches=len(keyword_records),
        keyword_awarded_tenders=len(keyword_awarded_rows),
        keyword_failed_awards=len(keyword_failed_rows),
    )


def build_drive_service(service_account_info: dict[str, Any]):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def build_drive_oauth_service(config: dict[str, Any]):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    required = ["client_id", "client_secret", "refresh_token"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise RuntimeError(f"Google Drive OAuth config missing keys: {', '.join(missing)}")
    credentials = Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        token_uri=config.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def build_configured_drive_service() -> tuple[Any, str]:
    oauth_raw = os.getenv("GOOGLE_DRIVE_OAUTH_CONFIG")
    if oauth_raw:
        try:
            oauth_config = json.loads(oauth_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_DRIVE_OAUTH_CONFIG must be valid JSON") from exc
        print("drive_auth=oauth")
        account = oauth_config.get("email") or oauth_config.get("sender") or "google user"
        return build_drive_oauth_service(oauth_config), account

    service_account_info = load_json_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    print("drive_auth=service_account")
    return build_drive_service(service_account_info), service_account_info.get("client_email", "unknown service account")


def list_visible_drive_folders(service) -> list[dict[str, str]]:
    response = execute_drive_request(
        service.files()
        .list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id,name,owners(displayName,emailAddress))",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageSize=20,
        ),
        "list_visible_drive_folders",
    )
    return response.get("files", [])


def execute_drive_request(request: Any, operation: str) -> dict[str, Any]:
    from googleapiclient.errors import HttpError

    for attempt, delay in enumerate([0, *DRIVE_RETRY_DELAYS_SECONDS], start=1):
        if delay:
            time.sleep(delay)
        try:
            return request.execute()
        except HttpError as exc:
            status = int(getattr(exc.resp, "status", 0) or 0)
            if status not in DRIVE_RETRY_STATUSES or attempt > len(DRIVE_RETRY_DELAYS_SECONDS):
                raise
            print(f"drive_api_retry={operation} status={status} attempt={attempt}")
    raise RuntimeError(f"Google Drive request did not complete: {operation}")


def assert_drive_folder_access(service, folder_id: str, drive_account: str) -> None:
    from googleapiclient.errors import HttpError

    print(f"drive_account={drive_account}")
    print(f"drive_folder_id={folder_id}")
    try:
        folder = execute_drive_request(
            service.files()
            .get(
                fileId=folder_id,
                fields="id,name,mimeType,owners(displayName,emailAddress)",
                supportsAllDrives=True,
            ),
            "get_drive_folder",
        )
    except HttpError as exc:
        if exc.resp.status != 404:
            raise
        visible = list_visible_drive_folders(service)
        visible_summary = ", ".join(f"{item.get('name')} ({item.get('id')})" for item in visible) or "none"
        raise RuntimeError(
            "Google Drive folder is not visible to the configured Drive account. "
            f"Share the target folder with {drive_account} as Editor, then rerun. "
            f"Visible folders for this account: {visible_summary}"
        ) from exc

    if folder.get("mimeType") != "application/vnd.google-apps.folder":
        raise RuntimeError(f"GOOGLE_DRIVE_FOLDER_ID is not a folder: {folder_id}")
    print(f"drive_folder_name={folder.get('name')}")


def drive_query_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def find_drive_file_by_name(service, folder_id: str, file_name: str) -> dict[str, str] | None:
    folder = drive_query_literal(folder_id)
    name = drive_query_literal(file_name)
    response = execute_drive_request(
        service.files()
        .list(
            q=f"name='{name}' and '{folder}' in parents and trashed=false",
            fields=f"files({DRIVE_FILE_FIELDS})",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            orderBy="createdTime desc",
            pageSize=1,
        ),
        "find_drive_file_by_name",
    )
    files = response.get("files", [])
    return files[0] if files else None


def make_drive_file_public(service, file_id: str) -> None:
    from googleapiclient.errors import HttpError

    try:
        execute_drive_request(
            service.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"},
                fields="id",
                supportsAllDrives=True,
            ),
            "create_drive_permission",
        )
    except HttpError as exc:
        status = int(getattr(exc.resp, "status", 0) or 0)
        content = getattr(exc, "content", b"")
        if status in {400, 403} and b"already" in content.lower() and b"permission" in content.lower():
            print(f"drive_permission=already_public file_id={file_id}")
            return
        raise


def refresh_drive_file(service, file_id: str) -> dict[str, str]:
    return execute_drive_request(
        service.files().get(fileId=file_id, fields=DRIVE_FILE_FIELDS, supportsAllDrives=True),
        "refresh_drive_file",
    )


def upload_to_drive(
    output_path: Path,
    folder_id: str,
    skip_if_exists: bool = False,
    notify_if_exists: bool = False,
) -> UploadResult:
    from googleapiclient.http import MediaFileUpload

    service, drive_account = build_configured_drive_service()
    folder_id = folder_id.strip()
    assert_drive_folder_access(service, folder_id, drive_account)
    if skip_if_exists:
        existing = find_drive_file_by_name(service, folder_id, output_path.name)
        if existing:
            print(f"drive_existing_file_id={existing.get('id')}")
            if notify_if_exists:
                file_id = existing["id"]
                make_drive_file_public(service, file_id)
                refreshed = refresh_drive_file(service, file_id)
                return UploadResult(
                    file_id=file_id,
                    web_view_link=refreshed.get("webViewLink", existing.get("webViewLink", "")),
                    web_content_link=refreshed.get("webContentLink", existing.get("webContentLink", "")),
                    created=False,
                )
            return UploadResult(
                file_id=existing["id"],
                web_view_link=existing.get("webViewLink", ""),
                web_content_link=existing.get("webContentLink", ""),
                created=False,
            )

    media = MediaFileUpload(str(output_path), mimetype=EXCEL_MIME_TYPE, resumable=False)
    metadata = {
        "name": output_path.name,
        "parents": [folder_id],
        "mimeType": EXCEL_MIME_TYPE,
    }
    created = execute_drive_request(
        service.files().create(body=metadata, media_body=media, fields=DRIVE_FILE_FIELDS, supportsAllDrives=True),
        "create_drive_file",
    )
    file_id = created["id"]
    make_drive_file_public(service, file_id)
    refreshed = refresh_drive_file(service, file_id)
    return UploadResult(
        file_id=file_id,
        web_view_link=refreshed.get("webViewLink", ""),
        web_content_link=refreshed.get("webContentLink", ""),
        created=True,
    )


def send_line_message(message: str) -> None:
    token = get_required_env("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = get_required_env("LINE_USER_ID")
    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": message}]},
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"LINE push failed: HTTP {response.status_code} {response.text}")


def gmail_api_credentials(config: dict[str, Any]):
    from google.oauth2.credentials import Credentials

    required = ["client_id", "client_secret", "refresh_token"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise RuntimeError(f"Gmail OAuth config missing keys: {', '.join(missing)}")
    return Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        token_uri=config.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )


def send_gmail_api(config: dict[str, Any], to_addr: str, subject: str, body: str) -> None:
    from googleapiclient.discovery import build

    sender = config.get("sender") or config.get("from") or to_addr
    message = EmailMessage()
    message["To"] = to_addr
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(body)

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    service = build("gmail", "v1", credentials=gmail_api_credentials(config), cache_discovery=False)
    service.users().messages().send(userId="me", body={"raw": encoded}).execute()


def send_smtp(config: dict[str, Any], to_addr: str, subject: str, body: str) -> None:
    sender = config.get("sender") or config.get("username")
    if not sender:
        raise RuntimeError("SMTP config requires sender or username")
    message = EmailMessage()
    message["To"] = to_addr
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(body)

    host = config.get("host", "smtp.gmail.com")
    port = int(config.get("port", 587))
    username = config.get("username")
    password = config.get("password")
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if config.get("use_tls", True):
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


def send_gmail_notification(subject: str, body: str) -> None:
    config_raw = os.getenv("GMAIL_CLIENT_OR_SERVICE_CONFIG")
    to_addr = os.getenv("GMAIL_NOTIFY_TO")
    if not config_raw or not to_addr:
        print("Gmail notification skipped: missing GMAIL_CLIENT_OR_SERVICE_CONFIG or GMAIL_NOTIFY_TO")
        return

    try:
        config = json.loads(config_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GMAIL_CLIENT_OR_SERVICE_CONFIG must be valid JSON") from exc

    config_type = config.get("type", "gmail_oauth")
    if config_type == "smtp":
        send_smtp(config, to_addr, subject, body)
        return
    if config_type in {"gmail_oauth", "oauth"}:
        send_gmail_api(config, to_addr, subject, body)
        return
    raise RuntimeError(f"Unsupported Gmail config type: {config_type}")


def success_message(export_result: ExportResult, upload_result: UploadResult) -> str:
    return "\n".join(
        [
            "PCC 勞務標案 Excel 已更新",
            f"日期: {export_result.target_date.isoformat()}",
            f"關鍵字公告: {export_result.keyword_matches}",
            f"關鍵字決標: {export_result.keyword_awarded_tenders}",
            f"關鍵字無法決標: {export_result.keyword_failed_awards}",
            f"Excel: {upload_result.web_view_link}",
        ]
    )


def summary_body(export_result: ExportResult, upload_result: UploadResult) -> str:
    return "\n".join(
        [
            "每週 PCC 勞務標案自動化摘要",
            "",
            f"最新執行日期: {datetime.now().isoformat(timespec='seconds')}",
            f"資料日期: {export_result.target_date.isoformat()}",
            f"Excel 檔名: {export_result.output_path.name}",
            f"Google Drive file id: {upload_result.file_id}",
            f"Excel 連結: {upload_result.web_view_link}",
            "",
            f"關鍵字公告: {export_result.keyword_matches}",
            f"關鍵字決標: {export_result.keyword_awarded_tenders}",
            f"關鍵字無法決標: {export_result.keyword_failed_awards}",
        ]
    )


def run(args: argparse.Namespace) -> int:
    output_path = Path(args.output).expanduser().resolve()
    try:
        export_result = export_excel(args.date, output_path, args.keywords)
        upload_result = upload_to_drive(
            export_result.output_path,
            get_required_env("GOOGLE_DRIVE_FOLDER_ID"),
            skip_if_exists=args.skip_if_drive_file_exists,
            notify_if_exists=args.notify_if_drive_file_exists,
        )
        if upload_result.created:
            send_line_message(success_message(export_result, upload_result))
        elif args.notify_if_drive_file_exists:
            send_line_message(success_message(export_result, upload_result))
            print("line_notification=sent_existing_drive_file")
        else:
            print("line_notification=skipped_existing_drive_file")
        if args.send_weekly_summary:
            send_gmail_notification(
                f"PCC 勞務標案每週摘要 {export_result.target_date.isoformat()}",
                summary_body(export_result, upload_result),
            )
        print(f"output={export_result.output_path}")
        print(f"drive_file_id={upload_result.file_id}")
        print(f"drive_link={upload_result.web_view_link}")
        print(f"keyword_matches={export_result.keyword_matches}")
        print(f"keyword_awarded_tenders={export_result.keyword_awarded_tenders}")
        print(f"keyword_failed_awards={export_result.keyword_failed_awards}")
        return 0
    except Exception:
        failure = traceback.format_exc()
        print(failure, file=sys.stderr)
        try:
            send_gmail_notification("PCC 勞務標案自動化失敗", failure)
        except Exception as notify_error:
            print(f"Gmail failure notification failed: {notify_error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PCC export, upload it to Drive, and send notifications.")
    parser.add_argument("--date", default="today", help="today or YYYY-MM-DD")
    parser.add_argument("--output", default="pcc_labor_tenders_today.xlsx", help="output xlsx path")
    parser.add_argument(
        "--keywords",
        default="委託,設計,監造,技術服務",
        help="comma-separated title keywords",
    )
    parser.add_argument(
        "--send-weekly-summary",
        action="store_true",
        help="send Gmail weekly summary after a successful run",
    )
    parser.add_argument(
        "--skip-if-drive-file-exists",
        action="store_true",
        help="skip LINE notification when a file with the same name already exists in the target Drive folder",
    )
    parser.add_argument(
        "--notify-if-drive-file-exists",
        action="store_true",
        help="send LINE notification with the existing Drive file link when a same-name file already exists",
    )
    return parser


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
