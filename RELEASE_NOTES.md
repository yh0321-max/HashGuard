# HashGuard v1.0.0

> 现代化文件哈希检验工具 — 首个正式版本

## 下载

| 文件 | 说明 |
|------|------|
| [HashGuard.exe](https://github.com/yh0321-max/HashGuard/releases/download/v1.0.0/HashGuard.exe) | Windows 单文件可执行程序 (12.4 MB) |
| [源代码 (zip)](https://github.com/yh0321-max/HashGuard/archive/refs/tags/v1.0.0.zip) | 完整源代码 |
| [源代码 (tar.gz)](https://github.com/yh0321-max/HashGuard/archive/refs/tags/v1.0.0.tar.gz) | 完整源代码 |

## 功能亮点

- 🧮 **单文件多算法并行计算** — 选中多种算法，一次读取同时计算出所有哈希值
- 🔍 **哈希对比验证** — 粘贴预期哈希值，自动匹配并高亮结果
- 📦 **批量处理** — 选择文件夹递归扫描，批量计算并支持 CSV 导出
- ✅ **校验文件验证** — 加载 `.md5` `.sha1` `.sha256` 等校验文件，自动识别算法并逐行验证
- 📋 **一键复制** — 点击复制按钮，按钮短暂变绿反馈已复制到剪贴板
- 🌓 **暗黑/明亮双主题** — 右上角一键切换，算法标签自动适配配色

## 支持的 9 种哈希算法

| 算法 | 位宽 | 类型 |
|------|------|------|
| MD5 | 128 bit | 加密 |
| SHA-1 | 160 bit | 加密 |
| SHA-256 | 256 bit | 加密 |
| SHA-512 | 512 bit | 加密 |
| SHA-3 (256 bit) | 256 bit | 加密 |
| BLAKE2b (256 bit) | 256 bit | 加密 |
| BLAKE3 | 256 bit | 加密 |
| xxHash (XXH64) | 64 bit | 非加密 |
| CRC32 | 32 bit | 校验 |

## 使用说明

### Windows 用户（推荐）

直接下载 `HashGuard.exe`，双击运行，无需安装任何依赖。

### 从源码运行

```bash
# 要求 Python 3.10+
git clone https://github.com/yh0321-max/HashGuard.git
cd HashGuard
pip install -r requirements.txt
python run.py
```

## 技术栈

- **GUI**: CustomTkinter (现代化 tkinter 封装)
- **打包**: PyInstaller (单文件 exe)
- **算法库**: hashlib (标准库) + xxhash + blake3
- **剪贴板**: pyperclip
- **语言**: Python 3.14

## 系统要求

- Windows 10/11 (exe)
- 或 Python 3.10+ (源码运行)
- macOS / Linux (源码运行)

---

*由 DeepSeek V4 Pro 独自开发并发布*
