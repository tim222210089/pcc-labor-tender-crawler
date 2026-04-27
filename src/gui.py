from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, ttk

from src.core import FetchConfig, StockCrawlerError, fetch_period_data, write_output


@dataclass(frozen=True)
class GuiRequest:
    stock_no: str
    display_month: str
    days: int
    dataset: str
    output_format: str
    output_path: Path


def default_output_path(
    stock_no: str,
    display_month: str,
    days: int,
    dataset: str,
    output_format: str,
) -> Path:
    return Path("output") / f"{stock_no}_{display_month}_{days}d_{dataset}.{output_format}"


class StockCrawlerGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("台股資料抓取器")
        self.root.minsize(780, 560)

        self._messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self._worker: threading.Thread | None = None

        self.stock_var = tk.StringVar()
        self.month_var = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        self.days_var = tk.StringVar(value="30")
        self.dataset_var = tk.StringVar(value="daily")
        self.output_format_var = tk.StringVar(value="csv")
        self.output_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="請輸入股票代碼、結束月份與天數。")

        self._build_ui()
        self.root.after(150, self._poll_messages)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding=18)
        container.grid(sticky="nsew")
        container.columnconfigure(1, weight=1)
        container.rowconfigure(8, weight=1)

        ttk.Label(container, text="股票代碼").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(container, textvariable=self.stock_var).grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(container, text="結束月份 (YYYY-MM)").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(container, textvariable=self.month_var).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(container, text="抓取天數").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        days_box = ttk.Combobox(
            container,
            textvariable=self.days_var,
            values=("30", "60", "90"),
            state="readonly",
        )
        days_box.grid(row=2, column=1, sticky="ew", pady=6)
        days_box.bind("<<ComboboxSelected>>", self._refresh_default_output_path)

        ttk.Label(container, text="資料類型").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=6)
        dataset_box = ttk.Combobox(
            container,
            textvariable=self.dataset_var,
            values=("daily", "average"),
            state="readonly",
        )
        dataset_box.grid(row=3, column=1, sticky="ew", pady=6)
        dataset_box.bind("<<ComboboxSelected>>", self._refresh_default_output_path)

        ttk.Label(container, text="輸出格式").grid(row=4, column=0, sticky="w", padx=(0, 12), pady=6)
        format_box = ttk.Combobox(
            container,
            textvariable=self.output_format_var,
            values=("csv", "json"),
            state="readonly",
        )
        format_box.grid(row=4, column=1, sticky="ew", pady=6)
        format_box.bind("<<ComboboxSelected>>", self._handle_format_change)

        ttk.Label(container, text="輸出檔案").grid(row=5, column=0, sticky="w", padx=(0, 12), pady=6)
        output_frame = ttk.Frame(container)
        output_frame.grid(row=5, column=1, sticky="ew", pady=6)
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_path_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_frame, text="瀏覽", command=self._browse_output_path).grid(row=0, column=1, padx=(8, 0))

        hint = "會從你指定的結束月份往前抓最近 30 / 60 / 90 天資料，並整合三大法人與融資融券。"
        ttk.Label(container, text=hint, foreground="#555555").grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(2, 8),
        )

        self.start_button = ttk.Button(container, text="開始抓取", command=self._start_fetch)
        self.start_button.grid(row=7, column=1, sticky="e", pady=(0, 10))

        ttk.Label(container, text="執行訊息").grid(row=8, column=0, sticky="nw", padx=(0, 12), pady=6)
        self.status_text = tk.Text(container, height=14, wrap="word", state="disabled")
        self.status_text.grid(row=8, column=1, sticky="nsew", pady=6)

        ttk.Label(container, textvariable=self.status_var, anchor="w").grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )

    def _append_status(self, message: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.insert("end", f"{message}\n")
        self.status_text.see("end")
        self.status_text.configure(state="disabled")
        self.status_var.set(message)

    def _browse_output_path(self) -> None:
        initial_path = self._suggest_output_path()
        output_format = self.output_format_var.get().strip().lower() or "csv"
        extension = f".{output_format}"
        selected = filedialog.asksaveasfilename(
            title="選擇輸出檔案",
            defaultextension=extension,
            filetypes=[
                (f"{output_format.upper()} files", f"*{extension}"),
                ("All files", "*.*"),
            ],
            initialfile=initial_path.name if initial_path.name else None,
            initialdir=str(initial_path.parent) if initial_path.parent else None,
        )
        if selected:
            self.output_path_var.set(selected)
            self._append_status(f"輸出路徑已設定：{selected}")

    def _suggest_output_path(self) -> Path:
        current = self.output_path_var.get().strip()
        if current:
            return Path(current)

        stock_no = self.stock_var.get().strip()
        display_month = self.month_var.get().strip()
        dataset = self.dataset_var.get().strip().lower() or "daily"
        output_format = self.output_format_var.get().strip().lower() or "csv"
        days = int(self.days_var.get().strip() or "30")

        if stock_no and display_month:
            return default_output_path(stock_no, display_month, days, dataset, output_format)
        return Path(".")

    def _refresh_default_output_path(self, _: object = None) -> None:
        if self.output_path_var.get().strip():
            return
        self.output_path_var.set(str(self._suggest_output_path()))

    def _handle_format_change(self, _: object = None) -> None:
        current = self.output_path_var.get().strip()
        if not current:
            self._refresh_default_output_path()
            return

        path = Path(current)
        new_suffix = f".{self.output_format_var.get().strip().lower()}"
        if path.suffix.lower() != new_suffix:
            self.output_path_var.set(str(path.with_suffix(new_suffix)))

    def _build_request(self) -> GuiRequest:
        stock_no = self.stock_var.get().strip()
        display_month = self.month_var.get().strip()
        dataset = self.dataset_var.get().strip().lower()
        output_format = self.output_format_var.get().strip().lower()
        days = int(self.days_var.get().strip())

        if not stock_no or not display_month or not dataset or not output_format:
            raise ValueError("股票代碼、結束月份、天數、資料類型與輸出格式都必須填寫。")

        output_path_text = self.output_path_var.get().strip()
        output_path = (
            Path(output_path_text)
            if output_path_text
            else default_output_path(stock_no, display_month, days, dataset, output_format)
        )

        return GuiRequest(
            stock_no=stock_no,
            display_month=display_month,
            days=days,
            dataset=dataset,
            output_format=output_format,
            output_path=output_path,
        )

    def _start_fetch(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            self._append_status("目前已有抓取工作正在執行。")
            return

        try:
            request = self._build_request()
            config = FetchConfig(
                stock_no=request.stock_no,
                month=request.display_month,
                display_month=request.display_month,
                days=request.days,
                dataset=request.dataset,
                output_format=request.output_format,
                output_path=request.output_path,
            )
        except ValueError as exc:
            self._append_status(f"輸入錯誤：{exc}")
            return
        except Exception:
            self._append_status("輸入錯誤：月份格式必須是 YYYY-MM。")
            return

        self.output_path_var.set(str(config.output_path))
        self._append_status(
            f"開始抓取 {config.stock_no} 截至 {config.display_month} 的最近 {config.days} 天資料..."
        )
        self.start_button.configure(state="disabled")

        self._worker = threading.Thread(
            target=self._run_fetch,
            args=(config,),
            name="stock-crawler-gui-worker",
            daemon=True,
        )
        self._worker.start()

    def _run_fetch(self, config: FetchConfig) -> None:
        try:
            result = fetch_period_data(config)
            write_output(result, config.output_path, config.output_format)
        except StockCrawlerError as exc:
            self._messages.put(("error", str(exc)))
            return
        except Exception as exc:
            self._messages.put(("error", f"未預期錯誤：{exc}"))
            return

        self._messages.put(
            (
                "success",
                f"已儲存 {config.stock_no} 截至 {config.display_month} 的最近 {config.days} 天 "
                f"{config.dataset} 資料到 {config.output_path.resolve()}",
            )
        )

    def _poll_messages(self) -> None:
        try:
            while True:
                level, message = self._messages.get_nowait()
                if level == "error":
                    self._append_status(f"抓取失敗：{message}")
                else:
                    self._append_status(message)
                self.start_button.configure(state="normal")
        except queue.Empty:
            pass
        finally:
            self.root.after(150, self._poll_messages)


def build_app() -> tk.Tk:
    root = tk.Tk()
    StockCrawlerGui(root)
    return root


def main() -> None:
    build_app().mainloop()


if __name__ == "__main__":
    main()
