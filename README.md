<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/algorithms-9-orange.svg" alt="Algorithms">
</p>

# HashGuard

> 现代化文件哈希检验工具 — 支持 9 种主流哈希算法，暗黑/明亮双主题，GUI 图形界面

HashGuard 是一款跨平台的桌面应用，提供直观的图形界面用于计算、对比和验证文件哈希值。支持从经典的 MD5 到最新的 BLAKE3 共 9 种算法，满足日常校验、安全审计、文件去重等场景需求。

---

## 功能特性

- **单文件多算法** — 一次选择多种算法并行计算，结果实时展示
- **哈希对比验证** — 输入预期哈希值，自动匹配并高亮结果
- **批量处理** — 选择文件夹递归扫描，批量计算所有文件，支持 CSV 导出
- **校验文件验证** — 加载 `.md5` / `.sha256` / `.sha1` 等校验文件，自动识别算法并逐行验证
- **一键复制** — 每条哈希值旁有复制按钮，点击后按钮变绿反馈
- **暗黑/明亮主题** — 右上角一键切换，算法标签自动适配配色
- **流式读取** — 大文件分块处理，进度条实时反馈，内存友好
- **跨平台** — Windows / macOS / Linux 均可运行

## 支持的算法

| 算法 | 位宽 | 类型 | 速度 | 说明 |
|------|------|------|------|------|
| **MD5** | 128 bit | 加密 | 快 | 经典消息摘要，不推荐安全场景 |
| **SHA-1** | 160 bit | 加密 | 快 | 曾广泛使用，现已不推荐 |
| **SHA-256** | 256 bit | 加密 | 中 | SHA-2 家族，广泛使用 |
| **SHA-512** | 512 bit | 加密 | 中 | 更高安全性 |
| **SHA-3 (256 bit)** | 256 bit | 加密 | 中 | 最新 SHA-3 标准 (Keccak) |
| **BLAKE2b (256 bit)** | 256 bit | 加密 | 快 | 比 MD5/SHA 更快更安全 |
| **BLAKE3** | 256 bit | 加密 | 极快 | 多线程优化，极致性能 |
| **xxHash (XXH64)** | 64 bit | 非加密 | 极快 | 适合数据去重 |
| **CRC32** | 32 bit | 校验 | 极快 | 循环冗余校验 |

## 界面预览

```
┌─────────────────────────────────────────────────────┐
│  HashGuard                             暗黑模式     │
│  ┌──────────┬──────────────┬────────────────────┐  │
│  │  单文件  │   批量处理    │    校验文件         │  │
│  ├──────────┴──────────────┴────────────────────┤  │
│  │  文件: [C:\...\file.iso]           [浏览...]  │  │
│  │  算法: MD5  SHA-1  SHA-256 ...    [计算哈希]  │  │
│  │  ████████████████░░░░  45%                    │  │
│  │  ┌──────────────────────────────────────┐      │  │
│  │  │  MD5      a1b2c3d4e5f6...    [复制]  │      │  │
│  │  │  SHA-256  e5f6a7b8c9d0...    [复制]  │      │  │
│  │  │  SHA-3    1a2b3c4d5e6f...    [复制]  │      │  │
│  │  └──────────────────────────────────────┘      │  │
│  │  对比: [___________________] [粘贴]  匹配     │  │
│  └─────────────────────────────────────────────────┘
│  HashGuard v1.0 | 支持 9 种哈希算法 | 就绪          │
└─────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python **3.10+**
- pip

### 安装

```bash
# 克隆仓库
git clone https://github.com/yh0321-max/HashGuard.git
cd HashGuard

# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
# 模块方式启动（推荐）
python -m hashguard.main

# 或直接运行脚本
python hashguard/main.py
```

### 依赖说明

| 包 | 用途 |
|----|------|
| `customtkinter` | 现代化 GUI 框架 |
| `xxhash` | xxHash 算法支持 |
| `blake3` | BLAKE3 算法支持 |
| `pyperclip` | 跨平台剪贴板操作 |

> 其余算法（MD5、SHA 系列、BLAKE2b、CRC32）由 Python 标准库 `hashlib` / `zlib` 提供，无需额外安装。

## 项目结构

```
HashGuard/
├── hashguard/
│   ├── __init__.py          # 包初始化
│   ├── main.py              # 程序入口
│   ├── app.py               # GUI 界面 (CustomTkinter)
│   │   ├── HashGuardApp     # 主窗口 + 主题切换
│   │   ├── SingleFileTab    # 单文件哈希 & 对比
│   │   ├── BatchTab         # 批量处理 & CSV 导出
│   │   └── VerifyTab        # 校验文件验证
│   ├── hasher.py            # 哈希计算引擎 (流式/多算法并行)
│   ├── algorithms.py        # 算法注册表 (元数据/工厂)
│   ├── verify.py            # 校验文件解析与批量验证
│   └── utils.py             # 工具函数 (剪贴板/格式化/文件)
├── requirements.txt         # Python 依赖
└── README.md                # 项目说明
```

## 技术亮点

- **一次 I/O，多算法并行** — 读取文件时所有选中算法共享同一个数据流，避免重复磁盘读取
- **流式分块处理** — 默认 64KB 块大小，大文件不占满内存，进度回调实时反馈
- **主题感知配色** — `ThemeMixin` 混入类实现暗黑/明亮双配色，算法标签根据主题自动选择颜色
- **错误容错** — 文件不存在、权限不足等异常均返回结构化错误信息而非崩溃

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。

---

<p align="center">
  <sub>由 <b>DeepSeek V4 Pro</b> 独自编写并上传</sub>
</p>
