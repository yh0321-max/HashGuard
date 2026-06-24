"""工具函数 — 剪贴板、文件选择、格式化等。"""

import os
import subprocess
import sys
from tkinter import filedialog
from typing import Optional


# ── 剪贴板 ───────────────────────────────────────────────────────

def copy_to_clipboard(text: str) -> bool:
    """将文本复制到系统剪贴板。

    Returns:
        True 表示复制成功。
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass

    # 回退方案：使用系统命令
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, close_fds=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            process.communicate(input=text.encode("utf-16le"))
            return process.returncode == 0
        elif sys.platform == "darwin":
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0
        else:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE, close_fds=True
            )
            process.communicate(input=text.encode("utf-8"))
            return process.returncode == 0
    except Exception:
        return False


def paste_from_clipboard() -> str:
    """从系统剪贴板读取文本。"""
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception:
        pass

    try:
        if sys.platform == "win32":
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return text or ""
    except Exception:
        pass

    return ""


# ── 文件选择 ─────────────────────────────────────────────────────

def select_file(title: str = "选择文件") -> Optional[str]:
    """打开文件选择对话框，返回选中的文件路径。"""
    return filedialog.askopenfilename(title=title)


def select_files(title: str = "选择文件") -> tuple[str, ...]:
    """打开多文件选择对话框，返回选中的文件路径元组。"""
    return filedialog.askopenfilenames(title=title)


def select_directory(title: str = "选择文件夹") -> Optional[str]:
    """打开文件夹选择对话框，返回选中的文件夹路径。"""
    return filedialog.askdirectory(title=title)


def gather_files_from_path(path: str, recursive: bool = True) -> list[str]:
    """从文件夹路径收集所有文件。

    Args:
        path: 文件夹路径或文件路径。
        recursive: 是否递归子目录。

    Returns:
        文件路径列表。
    """
    if os.path.isfile(path):
        return [path]

    if not os.path.isdir(path):
        return []

    files = []
    if recursive:
        for root, _, filenames in os.walk(path):
            for f in filenames:
                files.append(os.path.join(root, f))
    else:
        for f in os.listdir(path):
            fp = os.path.join(path, f)
            if os.path.isfile(fp):
                files.append(fp)

    return sorted(files)


# ── 格式化 ───────────────────────────────────────────────────────

def format_file_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读的大小字符串。"""
    if size_bytes < 0:
        return "未知"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(size_bytes)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


def format_hash_display(hash_value: str, group_size: int = 8) -> str:
    """将哈希值格式化显示（每 N 个字符用空格分组）。

    Args:
        hash_value: 原始十六进制哈希字符串。
        group_size: 每组字符数。

    Returns:
        分组后的字符串。
    """
    if not hash_value:
        return ""
    return " ".join(
        hash_value[i:i + group_size] for i in range(0, len(hash_value), group_size)
    )


def format_hash_compact(hash_value: str) -> str:
    """返回紧凑格式的哈希值（全小写、无空格）。"""
    if not hash_value:
        return ""
    return hash_value.lower().replace(" ", "")


# ── 校验文件相关 ─────────────────────────────────────────────────

def parse_checksum_line(line: str) -> Optional[tuple[str, str]]:
    """解析校验文件中的一行。

    支持格式:
        <hash> <filename>
        <hash> *<filename>   (二进制模式标记)
        <hash>  <filename>

    Returns:
        (hash_string, filename) 或 None（如果无法解析）。
    """
    line = line.strip()
    if not line or line.startswith("#") or line.startswith(";"):
        return None

    # 移除二进制模式标记
    if " *" in line:
        parts = line.split(" *", 1)
    else:
        parts = line.split(None, 1)

    if len(parts) < 2:
        return None

    hash_str = parts[0].strip().lower()
    filename = parts[1].strip()

    return hash_str, filename
