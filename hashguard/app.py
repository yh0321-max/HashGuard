"""HashGuard GUI — 使用 CustomTkinter 构建的现代化哈希检验工具。"""

import os
import threading
from tkinter import messagebox

import customtkinter as ctk

from .algorithms import (
    ALL_ALGORITHMS,
    DEFAULT_SELECTED,
    Algorithm,
    ALGORITHM_MAP,
)
from .hasher import compute_hashes, FileHashResults
from .utils import (
    copy_to_clipboard,
    paste_from_clipboard,
    select_file,
    select_files,
    select_directory,
    gather_files_from_path,
    format_file_size,
    format_hash_display,
)
from .verify import (
    VerifyEntry,
    VerifyResult,
    parse_checksum_file,
    verify_checksum_file,
)

# ── 主题配置 ─────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 深色 / 明亮两套配色
DARK_COLORS = {
    "bg": "#1a1a2e",
    "card": "#16213e",
    "accent": "#0f3460",
    "highlight": "#e94560",
    "text": "#eaeaea",
    "text_dim": "#a0a0b0",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "info": "#3498db",
}

LIGHT_COLORS = {
    "bg": "#f5f5f5",
    "card": "#ffffff",
    "accent": "#d0e4f7",
    "highlight": "#c0392b",
    "text": "#1a1a2e",
    "text_dim": "#566573",
    "success": "#1e8449",
    "warning": "#d35400",
    "error": "#b03a2e",
    "info": "#2471a3",
}


def get_colors() -> dict[str, str]:
    """根据当前外观模式返回对应的配色方案。"""
    mode = ctk.get_appearance_mode().lower()
    return LIGHT_COLORS if mode == "light" else DARK_COLORS


# ── 主题感知混入 ─────────────────────────────────────────────────

class ThemeMixin:
    """为标签页提供主题切换支持。"""

    def _init_theme(self):
        """初始化主题追踪列表（子类 __init__ 中调用）。"""
        self._theme_widgets: list[tuple[ctk.CTkBaseClass, str]] = []  # (widget, color_role)

    def _track_color(self, widget, role: str):
        """记录需要随主题切换更新颜色的控件。"""
        self._theme_widgets.append((widget, role))

    def _apply_theme(self):
        """重新应用所有已追踪控件的颜色。"""
        c = get_colors()
        for widget, role in self._theme_widgets:
            try:
                widget.configure(text_color=c[role])
            except Exception:
                pass  # 控件可能已被销毁

    def _c(self, role: str) -> str:
        """获取当前主题下指定角色的颜色值。"""
        return get_colors()[role]


class SingleFileTab(ctk.CTkFrame, ThemeMixin):
    """单文件哈希计算标签页。"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._init_theme()

        self._selected_file: str = ""
        self._last_results: FileHashResults | None = None
        self._algorithm_vars: dict[str, ctk.BooleanVar] = {}
        self._result_widgets: list[dict] = []

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # results area expands

        # ── 标题 ──────────────────────────────────────────────
        title = ctk.CTkLabel(
            self, text="🔐 单文件哈希计算",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        desc = ctk.CTkLabel(
            self, text="选择一个文件，计算其哈希值，或与预期哈希值进行对比验证。",
            font=ctk.CTkFont(size=12),
            text_color=self._c("text_dim"),
        )
        desc.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        # ── 文件选择行 ────────────────────────────────────────
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(file_frame, text="📁 文件:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=(10, 5), pady=10
        )

        self._file_path_var = ctk.StringVar(value="尚未选择文件...")
        self._file_label = ctk.CTkLabel(
            file_frame,
            textvariable=self._file_path_var,
            font=ctk.CTkFont(size=12),
            text_color=self._c("text_dim"),
            anchor="w",
        )
        self._file_label.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        browse_btn = ctk.CTkButton(
            file_frame, text="浏览...", width=80,
            command=self._browse_file,
        )
        browse_btn.grid(row=0, column=2, padx=(5, 10), pady=10)

        # ── 算法选择 ──────────────────────────────────────────
        algo_frame = ctk.CTkFrame(self)
        algo_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(
            algo_frame, text="🔧 选择算法:",
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        checkboxes_frame = ctk.CTkFrame(algo_frame, fg_color="transparent")
        checkboxes_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        for i, alg in enumerate(ALL_ALGORITHMS):
            var = ctk.BooleanVar(value=alg.id in DEFAULT_SELECTED)
            self._algorithm_vars[alg.id] = var
            cb = ctk.CTkCheckBox(
                checkboxes_frame,
                text=alg.name,
                variable=var,
                font=ctk.CTkFont(size=12),
            )
            row, col = divmod(i, 3)
            cb.grid(row=row, column=col, padx=10, pady=4, sticky="w")

        # 计算按钮
        self._compute_btn = ctk.CTkButton(
            algo_frame, text="⚡ 计算哈希值", width=130,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._compute,
        )
        self._compute_btn.grid(row=0, column=2, padx=(30, 10), pady=10)

        # ── 进度条 ────────────────────────────────────────────
        self._progress = ctk.CTkProgressBar(self)
        self._progress.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="ew")
        self._progress.set(0)

        self._status_var = ctk.StringVar(value="")
        self._status_label = ctk.CTkLabel(
            self, textvariable=self._status_var,
            font=ctk.CTkFont(size=11),
            text_color=self._c("text_dim"),
        )
        self._track_color(self._status_label, "text_dim")
        self._status_label.grid(row=5, column=0, padx=20, pady=(0, 5), sticky="w")

        # ── 结果区域 ──────────────────────────────────────────
        self._results_scroll = ctk.CTkScrollableFrame(self)
        self._results_scroll.grid(row=7, column=0, padx=20, pady=(5, 10), sticky="nsew")
        self._results_scroll.grid_columnconfigure(0, weight=1)

        self._results_inner = ctk.CTkFrame(self._results_scroll, fg_color="transparent")
        self._results_inner.grid(row=0, column=0, sticky="ew")
        self._results_inner.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(7, weight=1)

        # ── 对比区域 ──────────────────────────────────────────
        compare_frame = ctk.CTkFrame(self)
        compare_frame.grid(row=8, column=0, padx=20, pady=(10, 20), sticky="ew")
        compare_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            compare_frame, text="🔍 对比验证:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self._compare_entry = ctk.CTkEntry(
            compare_frame,
            placeholder_text="在此粘贴预期哈希值进行对比...",
            font=ctk.CTkFont(size=12),
            height=32,
        )
        self._compare_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        paste_btn = ctk.CTkButton(
            compare_frame, text="📋 粘贴", width=70,
            command=self._paste_compare,
        )
        paste_btn.grid(row=0, column=2, padx=5, pady=10)

        self._compare_result_var = ctk.StringVar(value="")
        self._compare_label = ctk.CTkLabel(
            compare_frame,
            textvariable=self._compare_result_var,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._compare_label.grid(row=0, column=3, padx=(10, 10), pady=10, sticky="w")

        # 绑定输入事件
        self._compare_entry.bind("<KeyRelease>", lambda e: self._check_compare())

    # ── 操作方法 ──────────────────────────────────────────────────

    def _browse_file(self):
        path = select_file("选择要计算哈希的文件")
        if path:
            self._selected_file = path
            self._file_path_var.set(path)

    def _get_selected_algorithms(self) -> list[str]:
        return [aid for aid, var in self._algorithm_vars.items() if var.get()]

    def _compute(self):
        if not self._selected_file:
            messagebox.showwarning("提示", "请先选择一个文件。")
            return

        selected = self._get_selected_algorithms()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一种哈希算法。")
            return

        self._compute_btn.configure(state="disabled", text="⏳ 计算中...")
        self._progress.set(0)
        self._status_var.set("正在计算...")
        self._clear_results()

        def _progress_cb(read_bytes: int, total_bytes: int):
            self.after(0, lambda: self._progress.set(read_bytes / total_bytes))
            self.after(0, lambda: self._status_var.set(
                f"已处理 {format_file_size(read_bytes)} / {format_file_size(total_bytes)}"
            ))

        def _run():
            try:
                results = compute_hashes(
                    self._selected_file, selected, progress_callback=_progress_cb
                )
                self._last_results = results
                self.after(0, lambda: self._display_results(results))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _display_results(self, results: FileHashResults):
        self._progress.set(1)
        self._compute_btn.configure(state="normal", text="⚡ 计算哈希值")

        file_name = os.path.basename(results.file_path)
        self._status_var.set(
            f"✅ 完成 — {file_name} ({format_file_size(results.file_size)})"
        )

        # 清理旧结果
        self._clear_results()

        for i, r in enumerate(results.results):
            if not r.success:
                # 错误行
                err_label = ctk.CTkLabel(
                    self._results_inner,
                    text=f"❌ {r.algorithm_name}: {r.error_message}",
                    font=ctk.CTkFont(size=12),
                    text_color=self._c("error"),
                    anchor="w",
                )
                err_label.grid(row=i, column=0, columnspan=3, padx=10, pady=3, sticky="w")
                self._result_widgets.append({"type": "error", "widget": err_label})
                continue

            alg = ALGORITHM_MAP.get(r.algorithm_id)
            color = alg.get_color(ctk.get_appearance_mode()) if alg else self._c("text")

            # 算法名
            name_label = ctk.CTkLabel(
                self._results_inner,
                text=f"  {r.algorithm_name}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=color,
                anchor="w",
                width=150,
            )
            name_label.grid(row=i, column=0, padx=(10, 0), pady=4, sticky="w")

            # 哈希值
            hash_text = format_hash_display(r.hash_value, group_size=8)
            hash_label = ctk.CTkLabel(
                self._results_inner,
                text=hash_text,
                font=ctk.CTkFont(size=11, family="Consolas"),
                text_color=self._c("text"),
                anchor="w",
            )
            hash_label.grid(row=i, column=1, padx=5, pady=4, sticky="ew")

            # 复制按钮
            copy_btn = ctk.CTkButton(
                self._results_inner,
                text="📋",
                width=40,
                height=28,
                command=lambda v=r.hash_value, b=None: self._copy_hash(v, b),
            )
            copy_btn.grid(row=i, column=2, padx=(5, 10), pady=4)
            # 修正 lambda 闭包 — 绑定当前按钮
            copy_btn.configure(
                command=lambda v=r.hash_value, btn=copy_btn: self._copy_hash(v, btn)
            )

            self._result_widgets.append({
                "type": "result",
                "widgets": [name_label, hash_label, copy_btn],
                "hash": r.hash_value,
                "algorithm_id": r.algorithm_id,
            })

        # 触发对比检查
        self._check_compare()

    def _clear_results(self):
        for item in self._result_widgets:
            for w in item.get("widgets", [item.get("widget")]):
                if w:
                    w.destroy()
        self._result_widgets.clear()
        self._compare_result_var.set("")

    def _copy_hash(self, value: str, button: ctk.CTkButton | None = None):
        """复制哈希值到剪贴板，并提供视觉反馈。"""
        if copy_to_clipboard(value):
            # 按钮反馈：短暂变绿 + 显示 ✅
            if button is not None:
                original_text = button.cget("text")
                original_fg = button.cget("fg_color")
                button.configure(text="✅", fg_color=get_colors()["success"])
                self.after(1500, lambda: button.configure(
                    text=original_text, fg_color=original_fg
                ))

            # 状态栏反馈：绿色高亮
            self._status_var.set(f"✅ 已复制到剪贴板: {value}")
            self._status_label.configure(text_color=get_colors()["success"])
            self.after(2000, lambda: self._status_label.configure(
                text_color=self._c("text_dim")
            ))
        else:
            self._status_var.set("❌ 复制失败，请重试")
            if button is not None:
                original_text = button.cget("text")
                original_fg = button.cget("fg_color")
                button.configure(text="❌", fg_color=get_colors()["error"])
                self.after(1500, lambda btn=button, txt=original_text, fg=original_fg:
                    btn.configure(text=txt, fg_color=fg))

    def _paste_compare(self):
        text = paste_from_clipboard()
        if text:
            self._compare_entry.delete(0, "end")
            self._compare_entry.insert(0, text.strip())
            self._check_compare()

    def _check_compare(self):
        """对比用户输入的哈希值与计算结果。"""
        expected = self._compare_entry.get().strip()
        self._compare_result_var.set("")

        if not expected or not self._result_widgets:
            return

        # 先检查精确匹配
        for item in self._result_widgets:
            if item.get("type") != "result":
                continue
            if item["hash"].lower() == expected.lower():
                self._compare_result_var.set(f"✅ 匹配: {item['algorithm_id'].upper()}")
                self._compare_label.configure(text_color=get_colors()["success"])
                return

        # 部分匹配提示
        for item in self._result_widgets:
            if item.get("type") != "result":
                continue
            if expected.lower() in item["hash"].lower():
                self._compare_result_var.set(f"⚠️ 部分匹配: {item['algorithm_id'].upper()}")
                self._compare_label.configure(text_color=get_colors()["warning"])
                return

        # 不匹配
        self._compare_result_var.set("❌ 未找到匹配的哈希值")
        self._compare_label.configure(text_color=get_colors()["error"])

    def _on_error(self, msg: str):
        self._compute_btn.configure(state="normal", text="⚡ 计算哈希值")
        self._status_var.set(f"❌ 错误: {msg}")
        messagebox.showerror("错误", msg)


class BatchTab(ctk.CTkFrame, ThemeMixin):
    """批量处理标签页。"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._init_theme()

        self._selected_path: str = ""
        self._file_paths: list[str] = []
        self._algorithm_vars: dict[str, ctk.BooleanVar] = {}
        self._result_rows: list[dict] = []

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)  # table expands

        # 标题
        title = ctk.CTkLabel(
            self, text="📦 批量处理",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        desc = ctk.CTkLabel(
            self, text="选择一个文件夹或拖入多个文件，批量计算所有文件的哈希值。",
            font=ctk.CTkFont(size=12),
            text_color=self._c("text_dim"),
        )
        desc.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # 路径选择
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(path_frame, text="📁 路径:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=(10, 5), pady=10
        )
        self._path_var = ctk.StringVar(value="未选择...")
        ctk.CTkLabel(
            path_frame, textvariable=self._path_var,
            font=ctk.CTkFont(size=12),
            text_color=self._c("text_dim"),
            anchor="w",
        ).grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        ctk.CTkButton(
            path_frame, text="📂 文件夹", width=80, command=self._browse_folder,
        ).grid(row=0, column=2, padx=5, pady=10)
        ctk.CTkButton(
            path_frame, text="📄 文件", width=80, command=self._browse_files,
        ).grid(row=0, column=3, padx=(0, 10), pady=10)

        # 算法选择 + 计算
        algo_frame = ctk.CTkFrame(self)
        algo_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(algo_frame, text="🔧 算法:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=(10, 5), pady=10, sticky="w"
        )

        cb_frame = ctk.CTkFrame(algo_frame, fg_color="transparent")
        cb_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        for i, alg in enumerate(ALL_ALGORITHMS):
            var = ctk.BooleanVar(value=alg.id in DEFAULT_SELECTED)
            self._algorithm_vars[alg.id] = var
            row_c, col_c = divmod(i, 3)
            ctk.CTkCheckBox(
                cb_frame, text=alg.name, variable=var, font=ctk.CTkFont(size=12),
            ).grid(row=row_c, column=col_c, padx=10, pady=4, sticky="w")

        self._batch_btn = ctk.CTkButton(
            algo_frame, text="⚡ 批量计算", width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._compute_batch,
        )
        self._batch_btn.grid(row=0, column=2, padx=(30, 10), pady=10)

        self._export_btn = ctk.CTkButton(
            algo_frame, text="📊 导出 CSV", width=100,
            command=self._export_csv,
        )
        self._export_btn.grid(row=0, column=3, padx=(0, 10), pady=10)

        # 进度
        self._batch_progress = ctk.CTkProgressBar(self)
        self._batch_progress.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="ew")
        self._batch_progress.set(0)

        self._batch_status_var = ctk.StringVar(value="")
        batch_status_lbl = ctk.CTkLabel(
            self, textvariable=self._batch_status_var,
            font=ctk.CTkFont(size=11),
            text_color=self._c("text_dim"),
        )
        batch_status_lbl.grid(row=5, column=0, padx=20, pady=(0, 5), sticky="w")

        # 结果表格（可滚动）
        self._table_scroll = ctk.CTkScrollableFrame(self)
        self._table_scroll.grid(row=6, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self._table_scroll.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

    def _browse_folder(self):
        path = select_directory("选择要处理的文件夹")
        if path:
            self._selected_path = path
            self._file_paths = gather_files_from_path(path, recursive=True)
            self._path_var.set(f"{path} ({len(self._file_paths)} 个文件)")

    def _browse_files(self):
        paths = select_files("选择要处理的文件")
        if paths:
            self._file_paths = list(paths)
            self._selected_path = os.path.dirname(paths[0]) if paths else ""
            self._path_var.set(f"已选择 {len(self._file_paths)} 个文件")

    def _get_selected_algorithms(self) -> list[str]:
        return [aid for aid, var in self._algorithm_vars.items() if var.get()]

    def _compute_batch(self):
        if not self._file_paths:
            messagebox.showwarning("提示", "请先选择文件或文件夹。")
            return

        selected = self._get_selected_algorithms()
        if not selected:
            messagebox.showwarning("提示", "请至少选择一种哈希算法。")
            return

        self._batch_btn.configure(state="disabled", text="⏳ 计算中...")
        self._batch_progress.set(0)
        self._clear_table()

        total = len(self._file_paths)

        def _run():
            all_results = []
            for idx, fp in enumerate(self._file_paths):
                try:
                    r = compute_hashes(fp, selected)
                    all_results.append(r)
                except Exception as e:
                    all_results.append(FileHashResults(
                        file_path=fp, file_size=0,
                        results=[],
                    ))
                self.after(0, lambda i=idx: self._batch_progress.set((i + 1) / total))
                self.after(0, lambda i=idx: self._batch_status_var.set(
                    f"处理中: {i + 1} / {total}"
                ))
            self.after(0, lambda: self._display_batch_results(all_results, selected))

        threading.Thread(target=_run, daemon=True).start()

    def _display_batch_results(self, all_results: list[FileHashResults], algo_ids: list[str]):
        self._batch_btn.configure(state="normal", text="⚡ 批量计算")
        self._batch_progress.set(1)
        self._batch_status_var.set(f"✅ 完成 — {len(all_results)} 个文件")

        # 表头
        header_frame = ctk.CTkFrame(self._table_scroll)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        header_frame.grid_columnconfigure(0, weight=1)

        header_text = "  文件名"
        for aid in algo_ids:
            alg = ALGORITHM_MAP.get(aid)
            header_text += f"    {alg.name if alg else aid}"
        ctk.CTkLabel(
            header_frame, text=header_text,
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=self._c("text_dim"),
            anchor="w",
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # 数据行
        for row_idx, fr in enumerate(all_results):
            row_frame = ctk.CTkFrame(self._table_scroll)
            row_frame.grid(row=row_idx + 1, column=0, sticky="ew", pady=1)
            row_frame.grid_columnconfigure(0, weight=1)

            fname = os.path.basename(fr.file_path)
            row_text = f"  {fname}"
            for aid in algo_ids:
                r = fr.get_result(aid)
                if r and r.success:
                    row_text += f"    {r.hash_value[:16]}..."
                else:
                    row_text += "    ERROR"

            lbl = ctk.CTkLabel(
                row_frame, text=row_text,
                font=ctk.CTkFont(size=10, family="Consolas"),
                anchor="w",
            )
            lbl.grid(row=0, column=0, padx=10, pady=3, sticky="w")
            self._result_rows.append({"widgets": [row_frame, lbl], "results": fr})

    def _clear_table(self):
        for item in self._result_rows:
            for w in item.get("widgets", []):
                w.destroy()
        self._result_rows.clear()

        # 清理表格框架中的所有子组件
        for child in self._table_scroll.winfo_children():
            child.destroy()

    def _export_csv(self):
        if not self._result_rows:
            messagebox.showwarning("提示", "没有可导出的结果。")
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="导出 CSV",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return

        algo_ids = self._get_selected_algorithms()
        with open(path, "w", encoding="utf-8-sig") as f:
            # 表头
            headers = ["文件名", "文件大小"] + [ALGORITHM_MAP.get(aid, Algorithm(id=aid, name=aid, hash_length=0, color="", color_light="", description="", hasher_factory=lambda: None)).name for aid in algo_ids]
            f.write(",".join(headers) + "\n")

            for item in self._result_rows:
                fr: FileHashResults = item["results"]
                fname = os.path.basename(fr.file_path)
                size = str(fr.file_size)
                values = [f'"{fname}"', size]
                for aid in algo_ids:
                    r = fr.get_result(aid)
                    values.append(r.hash_value if r and r.success else "ERROR")
                f.write(",".join(values) + "\n")

        messagebox.showinfo("导出成功", f"结果已导出到:\n{path}")


class VerifyTab(ctk.CTkFrame, ThemeMixin):
    """校验文件验证标签页。"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._init_theme()

        self._checksum_path: str = ""
        self._verify_entries: list[VerifyEntry] = []
        self._entry_widgets: list[dict] = []

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 标题
        title = ctk.CTkLabel(
            self, text="✅ 校验文件验证",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        desc = ctk.CTkLabel(
            self, text="加载 .md5 / .sha256 等校验文件，自动验证所有条目的完整性。",
            font=ctk.CTkFont(size=12),
            text_color=self._c("text_dim"),
        )
        desc.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # 校验文件选择
        cf_frame = ctk.CTkFrame(self)
        cf_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        cf_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cf_frame, text="📄 校验文件:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=(10, 5), pady=10
        )
        self._checksum_var = ctk.StringVar(value="未选择校验文件...")
        ctk.CTkLabel(
            cf_frame, textvariable=self._checksum_var,
            font=ctk.CTkFont(size=12),
            text_color=self._c("text_dim"),
            anchor="w",
        ).grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        ctk.CTkButton(
            cf_frame, text="浏览...", width=80, command=self._browse_checksum,
        ).grid(row=0, column=2, padx=5, pady=10)

        self._verify_btn = ctk.CTkButton(
            cf_frame, text="🔍 开始验证", width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._run_verify,
        )
        self._verify_btn.grid(row=0, column=3, padx=(0, 10), pady=10)

        # 统计栏
        stats_frame = ctk.CTkFrame(self)
        stats_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        self._stats_var = ctk.StringVar(value="就绪")
        ctk.CTkLabel(
            stats_frame, textvariable=self._stats_var,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=15, pady=8)

        # 结果区域
        self._verify_scroll = ctk.CTkScrollableFrame(self)
        self._verify_scroll.grid(row=4, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self._verify_scroll.grid_columnconfigure(0, weight=1)

    def _browse_checksum(self):
        path = select_file("选择校验文件")
        if not path:
            return

        self._checksum_path = path
        self._checksum_var.set(path)
        self._clear_entries()

        # 预解析并显示条目
        entries = parse_checksum_file(path)
        self._verify_entries = entries
        self._display_entries_preview(entries)

    def _display_entries_preview(self, entries: list[VerifyEntry]):
        self._clear_entries()

        if not entries:
            ctk.CTkLabel(
                self._verify_scroll, text="校验文件为空或格式不正确。",
                font=ctk.CTkFont(size=12),
                text_color=self._c("text_dim"),
            ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
            return

        self._stats_var.set(f"📋 共 {len(entries)} 条记录，点击「开始验证」进行校验")

        for i, entry in enumerate(entries):
            row = ctk.CTkFrame(self._verify_scroll)
            row.grid(row=i, column=0, sticky="ew", pady=1)
            row.grid_columnconfigure(1, weight=1)

            status_icon = "⏳" if entry.status == "pending" else "❓"
            icon_lbl = ctk.CTkLabel(row, text=status_icon, font=ctk.CTkFont(size=14), width=30)
            icon_lbl.grid(row=0, column=0, padx=(5, 0), pady=2)

            file_lbl = ctk.CTkLabel(
                row, text=entry.filename,
                font=ctk.CTkFont(size=11),
                anchor="w",
            )
            file_lbl.grid(row=0, column=1, padx=5, pady=2, sticky="w")

            hash_lbl = ctk.CTkLabel(
                row, text=entry.expected_hash,
                font=ctk.CTkFont(size=10, family="Consolas"),
                text_color=self._c("text_dim"),
                anchor="w",
            )
            hash_lbl.grid(row=0, column=2, padx=5, pady=2, sticky="w")

            status_lbl = ctk.CTkLabel(row, text="等待中", font=ctk.CTkFont(size=11), width=60)
            status_lbl.grid(row=0, column=3, padx=(5, 10), pady=2)

            self._entry_widgets.append({
                "row": row,
                "icon": icon_lbl,
                "file": file_lbl,
                "hash": hash_lbl,
                "status": status_lbl,
                "entry": entry,
            })

    def _run_verify(self):
        if not self._checksum_path:
            messagebox.showwarning("提示", "请先选择校验文件。")
            return

        self._verify_btn.configure(state="disabled", text="⏳ 验证中...")
        # 重置所有条目状态
        for ew in self._entry_widgets:
            ew["icon"].configure(text="⏳")
            ew["status"].configure(text="验证中...", text_color=self._c("text_dim"))

        def _update_progress(current: int, total: int):
            self.after(0, lambda: self._stats_var.set(f"验证中: {current} / {total}"))

        def _run():
            result = verify_checksum_file(
                self._checksum_path, progress_callback=_update_progress
            )
            self.after(0, lambda: self._display_verify_result(result))

        threading.Thread(target=_run, daemon=True).start()

    def _display_verify_result(self, result: VerifyResult):
        self._verify_btn.configure(state="normal", text="🔍 开始验证")

        match = result.match_count
        mismatch = result.mismatch_count
        error = result.error_count
        missing = result.missing_count

        self._stats_var.set(
            f"✅ 通过: {match}  |  ❌ 失败: {mismatch}  |  ⚠️ 错误: {error}  |  📁 缺失: {missing}"
        )

        for ew in self._entry_widgets:
            entry = ew["entry"]
            if entry.status == "match":
                ew["icon"].configure(text="✅")
                ew["status"].configure(text="通过", text_color=get_colors()["success"])
            elif entry.status == "mismatch":
                ew["icon"].configure(text="❌")
                ew["status"].configure(text="不匹配", text_color=get_colors()["error"])
            elif entry.status == "missing":
                ew["icon"].configure(text="📁")
                ew["status"].configure(text="文件缺失", text_color=get_colors()["warning"])
            else:
                ew["icon"].configure(text="⚠️")
                ew["status"].configure(text=entry.error_message or "错误", text_color=get_colors()["error"])

    def _clear_entries(self):
        for ew in self._entry_widgets:
            ew["row"].destroy()
        self._entry_widgets.clear()
        # 清理滚动框架中的残留
        for child in self._verify_scroll.winfo_children():
            child.destroy()


# ── 主应用窗口 ───────────────────────────────────────────────────

class HashGuardApp(ctk.CTk):
    """HashGuard 主应用。"""

    def __init__(self):
        super().__init__()

        self.title("HashGuard — 文件哈希检验工具")
        self.geometry("960x720")
        self.minsize(800, 600)

        # 设置图标（如果有的话）
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # tabview 行可拉伸

        # ── 顶部栏：标题 + 主题切换 ──────────────────────────
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar, text="🔐 HashGuard",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=(5, 10), pady=5, sticky="w")

        # 主题切换开关
        self._theme_switch = ctk.CTkSwitch(
            top_bar,
            text="🌙 暗黑模式",
            font=ctk.CTkFont(size=12),
            command=self._on_theme_toggle,
        )
        self._theme_switch.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="e")
        # 初始状态：暗黑模式选中
        self._theme_switch.select()

        # ── 标签页 ────────────────────────────────────────────
        self._tabview = ctk.CTkTabview(self)
        self._tabview.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # 创建标签
        self._tab_single = self._tabview.add("🔐 单文件")
        self._tab_batch = self._tabview.add("📦 批量处理")
        self._tab_verify = self._tabview.add("✅ 校验文件")

        # 填充内容
        self._single_tab = SingleFileTab(self._tab_single)
        self._single_tab.pack(fill="both", expand=True)

        self._batch_tab = BatchTab(self._tab_batch)
        self._batch_tab.pack(fill="both", expand=True)

        self._verify_tab = VerifyTab(self._tab_verify)
        self._verify_tab.pack(fill="both", expand=True)

        # ── 底部状态栏 ────────────────────────────────────────
        self._footer_var = ctk.StringVar(value="HashGuard v1.0  |  支持 9 种哈希算法  |  就绪")
        self._footer_label = ctk.CTkLabel(
            self, textvariable=self._footer_var,
            font=ctk.CTkFont(size=10),
            text_color=get_colors()["text_dim"],
        )
        self._footer_label.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="w")

    def _on_theme_toggle(self):
        """切换暗黑 / 明亮主题。"""
        if self._theme_switch.get():
            ctk.set_appearance_mode("dark")
            self._theme_switch.configure(text="🌙 暗黑模式")
        else:
            ctk.set_appearance_mode("light")
            self._theme_switch.configure(text="☀️ 明亮模式")

        # 更新页脚颜色
        self._footer_label.configure(text_color=get_colors()["text_dim"])

        # 通知所有标签页刷新颜色
        for tab in (self._single_tab, self._batch_tab, self._verify_tab):
            tab._apply_theme()


def run():
    """启动 HashGuard GUI。"""
    app = HashGuardApp()
    app.mainloop()
