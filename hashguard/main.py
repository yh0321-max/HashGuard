#!/usr/bin/env python3
"""HashGuard — 文件哈希检验工具

支持 9 种哈希算法:
    MD5, SHA-1, SHA-256, SHA-512, SHA-3 (256 bit),
    BLAKE2b (256 bit), BLAKE3, xxHash, CRC32

功能:
    - 单文件哈希计算与对比验证
    - 批量文件/文件夹哈希计算
    - 校验文件 (.md5, .sha256 等) 验证

用法:
    python -m hashguard.main          # 推荐：以模块方式启动
    python hashguard/main.py          # 也可直接运行脚本
"""

import sys
import os

# 确保项目根目录在 sys.path 中（支持直接运行 script 和模块导入两种方式）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main():
    if "--cli" in sys.argv:
        print("CLI 模式尚未实现，请使用 GUI 模式。")
        print("运行: python -m hashguard.main")
        sys.exit(0)

    # 兼容相对导入（模块运行）和绝对导入（脚本运行）
    try:
        from .app import run
    except ImportError:
        from hashguard.app import run

    run()


if __name__ == "__main__":
    main()
