# paper-to-skill

**将学术论文 PDF 转换为结构化的 Agent 技能 — 可在 Claude Code 或 OpenCode 中随时调用、学习和参考。**

[English](README.md) | 中文

## 项目介绍

paper-to-skill 能将一篇或多篇学术论文 PDF 转换为结构化的按需技能，供 AI 编程助手加载和推理使用。无需每次会话都重新阅读论文，只需一次性教会你的 Agent 论文中的方法、发现和框架。

生成的技能包括：
- **SKILL.md** — 核心贡献、研究动机、方法和可导航索引
- **sections/** — 按章节的摘要，包含关键概念、方法论、发现
- **glossary.md** — 所有技术术语及定义
- **methods.md** — 所有方法、算法和实验流程
- **cheatsheet.md** — 决策规则、对比表格、关键结果

## 支持的 Agent

| Agent | 个人技能目录 | 项目本地目录 |
|-------|-------------|-------------|
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` |
| **OpenCode** | `~/.opencode/skills/` | `.opencode/skills/` |

## 安装方式

### 方式一：通过 pip 安装（推荐）

```bash
pip install paper-to-skill
```

安装可选的 PDF 提取后端：

```bash
# 基础 PDF 提取
pip install paper-to-skill[pdf]

# 技术论文（表格、公式、算法）
pip install paper-to-skill[technical]

# 全部安装
pip install paper-to-skill[all]
```

### 方式二：作为 Agent 技能安装

**Claude Code：**
```bash
mkdir -p ~/.claude/skills/
git clone https://github.com/FireJason-404/paper-to-skill.git ~/.claude/skills/paper-to-skill/
```

**OpenCode：**
```bash
mkdir -p ~/.opencode/skills/
git clone https://github.com/FireJason-404/paper-to-skill.git ~/.opencode/skills/paper-to-skill/
```

### 方式三：从源码安装

```bash
git clone https://github.com/FireJason-404/paper-to-skill.git
cd paper-to-skill
pip install -e .
```

### PDF 提取依赖

至少需要安装一个 PDF 提取工具：

```bash
# 系统工具（推荐，最快）
sudo apt install poppler-utils

# 或 Python 包（任选其一即可）
pip install pypdf
# 或
pip install pdfminer.six

# 技术论文的表格/公式提取（可选）
pip install docling
```

## 使用方法

### 命令行使用

```bash
# 转换单篇论文
paper-to-skill ~/papers/attention-is-all-you-need.pdf

# 将多篇论文转换为一个技能
paper-to-skill ~/papers/*.pdf my-literature-review

# 指定技术模式提取
paper-to-skill ~/papers/paper.pdf --mode technical

# 检查已安装的提取工具
paper-to-skill --check
```

### 在 Claude Code / OpenCode 中使用

安装为技能后，在 Agent 中直接说：

```
paper-to-skill ~/papers/attention-is-all-you-need.pdf
```

或先分析再生成：

```
paper-to-skill ~/papers/paper.pdf
> analyze only
```

### Python API 使用

```python
from paper_to_skill.utils import extract_single_file, resolve_input_files
from pathlib import Path

# 解析输入文件
files = resolve_input_files(["~/papers/my-paper.pdf"])

# 提取文本和元数据
result = extract_single_file(files[0], extraction_mode="text", install_mode="no")
print(f"使用 {result['extraction_method']} 提取了 {result['words']} 个词")
```

## 操作模式

| 模式 | 触发方式 | 输出 |
|------|---------|------|
| **完整转换** | 提供 PDF 路径 | 包含所有文件的完整技能 |
| **仅分析** | 说 "analyze" 或 "analyze only" | 供审阅的提取报告 |
| **从分析生成** | 提供先前的分析笔记 | 基于分析生成的技能文件 |
| **更新/合并** | 指向已有技能 + 新 PDF | 合并新论文后的更新技能 |

## 论文类型

转换器会根据论文类型优化提取策略：

- **技术/定量型** — 机器学习、计算机科学、工程类论文（使用 Docling 提取表格、公式、算法）
- **文本/定性型** — 社会科学、人文、综述类论文（使用快速文本提取）

## 适用场景

paper-to-skill 适用于：

- 📚 **文献综述** — 从研究领域的多篇论文中构建可搜索的知识库
- 🔬 **方法实现** — 从论文中提取算法和方法，指导编程 Agent 进行实现
- 📝 **论文学习** — 创建结构化笔记供研究过程中快速参考
- 🤖 **Agent 增强** — 为 AI 助手注入学术论文中的领域知识
- 👥 **团队知识共享** — 生成可复用的技能文件供团队成员共享和参考
- 🎓 **学术写作** — 写作时快速引用关键发现、方法和贡献

## 输出结构

转换后生成的技能目录结构如下：

```
~/.claude/skills/vaswani-attention/
├── SKILL.md                    # 主索引，包含核心贡献（~4K tokens）
├── sections/
│   ├── 01-introduction.md      # 各章节摘要
│   ├── 02-background.md
│   ├── 03-methodology.md
│   ├── 04-results.md
│   └── 05-discussion.md
├── glossary.md                 # 所有技术术语（~1.5K tokens）
├── methods.md                  # 方法和算法（~2K tokens）
└── cheatsheet.md               # 决策规则和快速参考（~1.2K tokens）
```

每个章节文件包括：
- 核心思想和研究动机
- 关键概念的精确定义
- 方法论细节（方法章节）
- 公式和算法（技术论文）
- 带指标的关键发现
- 与相关章节的交叉引用

## 使用效果

- **使用前**：每次会话都要重新阅读论文，对话间丢失上下文，手动搜索方法
- **使用后**：Agent 按需加载论文知识，导航到相关章节，直接应用方法

典型转换效果：15 页论文 → 约 8K tokens 的技能（按需加载，非全部一次性加载）

## 项目结构

```
paper-to-skill/
├── SKILL.md                    # 主技能定义文件（安装此文件）
├── scripts/
│   └── extract.py              # PDF 文本提取入口
├── paper_to_skill/             # Python 包
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # CLI 入口
│   ├── config.py               # 配置常量
│   ├── dependencies.py         # 依赖管理
│   ├── exceptions.py           # 自定义异常
│   ├── utils.py                # 主提取逻辑
│   └── parsers/
│       ├── __init__.py
│       └── pdf.py              # PDF 提取方法
├── tests/
├── pyproject.toml
├── README.md                   # 英文文档
└── README_zh.md                # 中文文档
```

## 系统要求

- Python >= 3.9
- 至少一个 PDF 提取工具：
  - `pdftotext`（来自 poppler-utils）— 推荐，最快
  - `pypdf` — 纯 Python 后备方案
  - `pdfminer.six` — 纯 Python 后备方案
  - `docling` — 用于含表格/公式的技术论文（可选）

## 依赖检查

运行预检命令查看已安装的工具：

```bash
paper-to-skill --check
# 或
python3 scripts/extract.py --check
```

## 致谢

本项目受 [@virgiliojr94](https://github.com/virgiliojr94) 的 [book-to-skill](https://github.com/virgiliojr94/book-to-skill) 启发并在其基础上改编。原项目将书籍转换为结构化的 Agent 技能。paper-to-skill 将这一概念适配到学术论文 PDF，增加了学术特定功能，如研究动机提取、方法论分析、假设识别，并支持 Claude Code 和 OpenCode 两种 Agent。

## 许可证

MIT
