"""HashGuard 启动器 — PyInstaller 打包入口"""

import os
import sys

# 确保 hashguard 包在路径中
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from hashguard.main import main

if __name__ == "__main__":
    main()
