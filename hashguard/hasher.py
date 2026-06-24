"""哈希计算引擎 — 流式读取、多算法并行计算、进度回调。"""

import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from .algorithms import Algorithm, ALL_ALGORITHMS, ALGORITHM_MAP

# 默认读取块大小: 64 KB
DEFAULT_CHUNK_SIZE = 64 * 1024


@dataclass
class HashResult:
    """单个算法的计算结果。"""

    algorithm_id: str
    algorithm_name: str
    hash_value: str
    success: bool = True
    error_message: str = ""

    @property
    def is_available(self) -> bool:
        return self.success and not self.error_message

    def __str__(self) -> str:
        if not self.success:
            return f"[{self.algorithm_name}] 错误: {self.error_message}"
        return self.hash_value


@dataclass
class FileHashResults:
    """一个文件的所有哈希计算结果。"""

    file_path: str
    file_size: int
    results: list[HashResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    def get_result(self, algorithm_id: str) -> Optional[HashResult]:
        for r in self.results:
            if r.algorithm_id == algorithm_id:
                return r
        return None


def compute_hashes(
    file_path: str,
    algorithm_ids: list[str],
    progress_callback: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> FileHashResults:
    """计算单个文件的多个哈希值。

    一次读取、同时喂给所有哈希对象，避免重复 I/O。

    Args:
        file_path: 文件路径。
        algorithm_ids: 要计算的算法 ID 列表。
        progress_callback: 进度回调 callback(已读字节数, 总字节数)。
        chunk_size: 每次读取的字节数。

    Returns:
        FileHashResults 包含所有算法的计算结果。
    """
    # 先检查文件是否存在
    try:
        file_size = os.path.getsize(file_path)
    except FileNotFoundError:
        return FileHashResults(
            file_path=file_path,
            file_size=0,
            results=[
                HashResult(algorithm_id="", algorithm_name="", hash_value="",
                           success=False, error_message=f"文件不存在: {file_path}")
            ],
        )
    except PermissionError:
        return FileHashResults(
            file_path=file_path,
            file_size=0,
            results=[
                HashResult(algorithm_id="", algorithm_name="", hash_value="",
                           success=False, error_message=f"权限不足: {file_path}")
            ],
        )
    except OSError as e:
        return FileHashResults(
            file_path=file_path,
            file_size=0,
            results=[
                HashResult(algorithm_id="", algorithm_name="", hash_value="",
                           success=False, error_message=f"无法访问文件: {e}")
            ],
        )

    results: list[HashResult] = []

    # 解析算法并创建哈希对象
    hashers: list[tuple[str, str, object]] = []  # (id, name, hasher)
    for aid in algorithm_ids:
        alg = ALGORITHM_MAP.get(aid)
        if alg is None:
            results.append(HashResult(
                algorithm_id=aid,
                algorithm_name=aid,
                hash_value="",
                success=False,
                error_message=f"未知算法: {aid}",
            ))
            continue
        try:
            h = alg.hasher_factory()
            hashers.append((alg.id, alg.name, h))
        except Exception as e:
            results.append(HashResult(
                algorithm_id=alg.id,
                algorithm_name=alg.name,
                hash_value="",
                success=False,
                error_message=f"初始化失败: {e}",
            ))

    # 流式读取并更新所有哈希对象
    bytes_read = 0
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                for _, _, h in hashers:
                    h.update(chunk)
                bytes_read += len(chunk)
                if progress_callback:
                    progress_callback(bytes_read, file_size)
    except PermissionError:
        return FileHashResults(
            file_path=file_path,
            file_size=file_size,
            results=[
                HashResult(algorithm_id="", algorithm_name="", hash_value="",
                           success=False, error_message="权限不足，无法读取文件")
            ],
        )
    except Exception as e:
        return FileHashResults(
            file_path=file_path,
            file_size=file_size,
            results=[
                HashResult(algorithm_id="", algorithm_name="", hash_value="",
                           success=False, error_message=f"读取文件失败: {e}")
            ],
        )

    # 收集结果
    for aid, aname, h in hashers:
        try:
            hash_value = h.hexdigest()
            results.append(HashResult(
                algorithm_id=aid,
                algorithm_name=aname,
                hash_value=hash_value,
                success=True,
            ))
        except Exception as e:
            results.append(HashResult(
                algorithm_id=aid,
                algorithm_name=aname,
                hash_value="",
                success=False,
                error_message=f"计算摘要失败: {e}",
            ))

    return FileHashResults(file_path=file_path, file_size=file_size, results=results)


def compute_hashes_batch(
    file_paths: list[str],
    algorithm_ids: list[str],
    file_progress_callback: Optional[Callable[[int, int], None]] = None,
    chunk_progress_callback: Optional[Callable[[int, int, int, int], None]] = None,
) -> list[FileHashResults]:
    """批量计算多个文件的哈希值。

    Args:
        file_paths: 文件路径列表。
        algorithm_ids: 要计算的算法 ID 列表。
        file_progress_callback: 文件级进度 callback(已完成文件数, 总文件数)。
        chunk_progress_callback: 字节级进度 callback(文件索引, 已读字节, 总文件数, 当前文件总字节)。

    Returns:
        FileHashResults 列表。
    """
    all_results: list[FileHashResults] = []
    total = len(file_paths)

    for idx, fp in enumerate(file_paths):
        def _chunk_cb(read_bytes: int, total_bytes: int):
            if chunk_progress_callback:
                chunk_progress_callback(idx, read_bytes, total, total_bytes)

        result = compute_hashes(fp, algorithm_ids, progress_callback=_chunk_cb)
        all_results.append(result)

        if file_progress_callback:
            file_progress_callback(idx + 1, total)

    return all_results


def iterative_hasher(file_path: str, algorithm_ids: list[str]):
    """返回一个生成器，逐块计算后 yield (algorithm_id, hexdigest)。

    适合在大文件处理中实时展示部分结果。

    Yields:
        tuple[str, str]: (algorithm_id, hexdigest so far) — 注意这只是中间值。
    """
    from .algorithms import ALGORITHM_MAP

    hashers_map: dict[str, object] = {}
    for aid in algorithm_ids:
        alg = ALGORITHM_MAP.get(aid)
        if alg:
            try:
                hashers_map[aid] = alg.hasher_factory()
            except Exception:
                pass

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(DEFAULT_CHUNK_SIZE)
            if not chunk:
                break
            for h in hashers_map.values():
                h.update(chunk)

    # 最终只返回完整结果
    for aid, h in hashers_map.items():
        yield aid, h.hexdigest()
