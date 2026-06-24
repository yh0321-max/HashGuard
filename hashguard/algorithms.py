"""算法注册表 — 定义所有支持的哈希算法及其元数据。"""

import hashlib
import zlib
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Algorithm:
    """单个哈希算法的完整描述。"""

    id: str
    name: str
    hash_length: int          # 十六进制输出的长度
    color: str                # 暗黑模式下的显示颜色
    color_light: str          # 明亮模式下的显示颜色
    description: str
    hasher_factory: Callable[[], object]  # 无参工厂函数，返回哈希对象
    requires_install: bool = False
    install_hint: str = ""

    @property
    def display_label(self) -> str:
        return f"{self.name} ({self.hash_length * 4} bit)" if self.hash_length else self.name

    def get_color(self, appearance_mode: str = "dark") -> str:
        """根据主题模式返回对应的颜色。"""
        return self.color_light if appearance_mode.lower() == "light" else self.color


# ── 内置 hashlib 工厂 ────────────────────────────────────────────

def _md5_factory():
    return hashlib.md5()


def _sha1_factory():
    return hashlib.sha1()


def _sha256_factory():
    return hashlib.sha256()


def _sha512_factory():
    return hashlib.sha512()


def _sha3_256_factory():
    return hashlib.sha3_256()


def _blake2b_factory():
    # BLAKE2b 256-bit (32 bytes)
    return hashlib.blake2b(digest_size=32)


# ── CRC32 包装（zlib 是流式的，需要手动聚合）────────────────────

class CRC32Wrapper:
    """将 zlib.crc32 包装成 hashlib 风格的 update/digest/hexdigest 接口。"""

    def __init__(self):
        self._crc = 0

    def update(self, data: bytes):
        self._crc = zlib.crc32(data, self._crc)

    def digest(self) -> bytes:
        # crc32 返回无符号 32 位整数
        return self._crc.to_bytes(4, byteorder="big")

    def hexdigest(self) -> str:
        return format(self._crc & 0xFFFFFFFF, "08x")


def _crc32_factory():
    return CRC32Wrapper()


# ── xxHash 工厂 ──────────────────────────────────────────────────

def _xxhash_factory():
    import xxhash
    return xxhash.xxh64()


# ── BLAKE3 工厂 ──────────────────────────────────────────────────

def _blake3_factory():
    import blake3
    return blake3.blake3()


# ── 注册表 ───────────────────────────────────────────────────────

ALL_ALGORITHMS: list[Algorithm] = [
    Algorithm(
        id="md5",
        name="MD5",
        hash_length=32,
        color="#E74C3C",
        color_light="#c0392b",
        description="MD5 消息摘要算法（128 bit），不推荐用于安全场景",
        hasher_factory=_md5_factory,
    ),
    Algorithm(
        id="sha1",
        name="SHA-1",
        hash_length=40,
        color="#E67E22",
        color_light="#d35400",
        description="安全哈希算法第一代（160 bit），不推荐用于安全场景",
        hasher_factory=_sha1_factory,
    ),
    Algorithm(
        id="sha256",
        name="SHA-256",
        hash_length=64,
        color="#2ECC71",
        color_light="#1e8449",
        description="SHA-2 家族 256 bit，广泛使用的安全哈希",
        hasher_factory=_sha256_factory,
    ),
    Algorithm(
        id="sha512",
        name="SHA-512",
        hash_length=128,
        color="#27AE60",
        color_light="#1a7a3a",
        description="SHA-2 家族 512 bit，高安全性哈希",
        hasher_factory=_sha512_factory,
    ),
    Algorithm(
        id="sha3_256",
        name="SHA-3 (256 bit)",
        hash_length=64,
        color="#3498DB",
        color_light="#2471a3",
        description="SHA-3 标准（Keccak），256 bit 输出",
        hasher_factory=_sha3_256_factory,
    ),
    Algorithm(
        id="blake2b_256",
        name="BLAKE2b (256 bit)",
        hash_length=64,
        color="#9B59B6",
        color_light="#7d3c98",
        description="BLAKE2b 算法，256 bit 输出，速度极快",
        hasher_factory=_blake2b_factory,
    ),
    Algorithm(
        id="blake3",
        name="BLAKE3",
        hash_length=64,
        color="#8E44AD",
        color_light="#6c3483",
        description="BLAKE3 — 极速哈希算法，256 bit 输出",
        hasher_factory=_blake3_factory,
        requires_install=True,
        install_hint="pip install blake3",
    ),
    Algorithm(
        id="xxhash",
        name="xxHash (XXH64)",
        hash_length=16,
        color="#1ABC9C",
        color_light="#0e6655",
        description="xxHash — 极速非加密哈希（64 bit）",
        hasher_factory=_xxhash_factory,
        requires_install=True,
        install_hint="pip install xxhash",
    ),
    Algorithm(
        id="crc32",
        name="CRC32",
        hash_length=8,
        color="#95A5A6",
        color_light="#5d6d7e",
        description="循环冗余校验（32 bit），常用于数据传输校验",
        hasher_factory=_crc32_factory,
    ),
]

# 按 ID 快速查找
ALGORITHM_MAP: dict[str, Algorithm] = {alg.id: alg for alg in ALL_ALGORITHMS}

# 默认选中的算法 ID
DEFAULT_SELECTED = {"md5", "sha256", "sha3_256"}


def get_algorithm(id: str) -> Optional[Algorithm]:
    """根据 ID 获取算法对象。"""
    return ALGORITHM_MAP.get(id)


def detect_algorithm_by_hash(hash_str: str) -> Optional[Algorithm]:
    """根据哈希字符串的长度推断算法类型。"""
    length = len(hash_str.strip())
    for alg in ALL_ALGORITHMS:
        if alg.hash_length == length:
            return alg
    return None
