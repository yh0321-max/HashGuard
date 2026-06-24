"""校验文件解析与验证。

支持常见校验文件格式:
    - .md5, .sha1, .sha256, .sha512 等
    - 格式: <hash> <filename> 或 <hash> *<filename>
    - 自动检测算法类型（根据哈希长度）
"""

import os
from dataclasses import dataclass, field

from .algorithms import Algorithm, detect_algorithm_by_hash
from .hasher import compute_hashes
from .utils import parse_checksum_line


@dataclass
class VerifyEntry:
    """单条校验记录。"""

    filename: str
    expected_hash: str
    actual_hash: str = ""
    algorithm: Algorithm = None  # type: ignore
    status: str = "pending"  # pending | match | mismatch | error | missing
    error_message: str = ""

    @property
    def is_match(self) -> bool:
        return self.status == "match"


@dataclass
class VerifyResult:
    """校验文件的完整验证结果。"""

    checksum_file_path: str
    algorithm: Algorithm = None  # type: ignore
    entries: list[VerifyEntry] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def match_count(self) -> int:
        return sum(1 for e in self.entries if e.status == "match")

    @property
    def mismatch_count(self) -> int:
        return sum(1 for e in self.entries if e.status == "mismatch")

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.entries if e.status == "error")

    @property
    def missing_count(self) -> int:
        return sum(1 for e in self.entries if e.status == "missing")


def parse_checksum_file(file_path: str) -> list[VerifyEntry]:
    """解析校验文件，提取所有条目。

    Args:
        file_path: 校验文件路径 (.md5, .sha256 等)。

    Returns:
        VerifyEntry 列表。
    """
    entries: list[VerifyEntry] = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return [VerifyEntry(filename="", expected_hash="", status="error", error_message=str(e))]

    for line in lines:
        parsed = parse_checksum_line(line)
        if parsed is None:
            continue
        hash_str, filename = parsed

        algorithm = detect_algorithm_by_hash(hash_str)
        entries.append(VerifyEntry(
            filename=filename,
            expected_hash=hash_str,
            algorithm=algorithm,
        ))

    return entries


def verify_checksum_file(
    checksum_path: str,
    progress_callback=None,
) -> VerifyResult:
    """验证校验文件中的所有条目。

    对每条记录：找到对应文件 -> 计算哈希 -> 对比。

    Args:
        checksum_path: 校验文件路径。
        progress_callback: 进度回调 callback(current_index, total)。

    Returns:
        VerifyResult 包含所有验证结果。
    """
    entries = parse_checksum_file(checksum_path)

    if entries and entries[0].status == "error":
        return VerifyResult(
            checksum_file_path=checksum_path,
            entries=entries,
        )

    # 推断算法：取第一个有效条目的算法
    detected_algorithm = None
    for entry in entries:
        if entry.algorithm is not None:
            detected_algorithm = entry.algorithm
            break

    # 如果无法检测到算法，尝试从文件名推断
    if detected_algorithm is None:
        basename = os.path.basename(checksum_path).lower()
        from .algorithms import ALL_ALGORITHMS
        for alg in ALL_ALGORITHMS:
            if alg.id in basename:
                detected_algorithm = alg
                break

    result = VerifyResult(
        checksum_file_path=checksum_path,
        algorithm=detected_algorithm,
        entries=entries,
    )

    # 校验文件所在目录作为基础路径
    base_dir = os.path.dirname(os.path.abspath(checksum_path))

    total = len(entries)
    for idx, entry in enumerate(entries):
        if progress_callback:
            progress_callback(idx, total)

        # 查找目标文件
        target_path = os.path.join(base_dir, entry.filename)
        if not os.path.exists(target_path):
            # 尝试直接在路径中查找
            if os.path.exists(entry.filename):
                target_path = entry.filename
            else:
                entry.status = "missing"
                entry.error_message = f"文件不存在: {entry.filename}"
                continue

        # 确定使用的算法
        alg = entry.algorithm or detected_algorithm
        if alg is None:
            entry.status = "error"
            entry.error_message = "无法检测校验算法"
            continue
        entry.algorithm = alg

        # 计算实际哈希值
        try:
            file_results = compute_hashes(target_path, [alg.id])
            hash_result = file_results.get_result(alg.id)

            if hash_result is None or not hash_result.success:
                entry.status = "error"
                entry.error_message = hash_result.error_message if hash_result else "计算失败"
                continue

            entry.actual_hash = hash_result.hash_value.lower()

            if entry.actual_hash == entry.expected_hash.lower():
                entry.status = "match"
            else:
                entry.status = "mismatch"
        except PermissionError:
            entry.status = "error"
            entry.error_message = "权限不足"
        except Exception as e:
            entry.status = "error"
            entry.error_message = str(e)

    if progress_callback:
        progress_callback(total, total)

    return result
