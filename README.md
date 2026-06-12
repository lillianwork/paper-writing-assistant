# 学术论文写作指挥中心 (Academic Writing Command Center)

一套集成 Claude Code + MCP + ARS 的学术论文写作全流程工具，将 AI 辅助学术写作的最佳实践打包为即开即用的客户端工作台。

## 核心组成

| 组件 | 说明 |
|------|------|
| **index.html** | 网页版写作工具：10 阶段管线、BRTR 提示词构建器、工具推荐、角色模拟、诚信闸门 |
| **CLAUDE.md** | Claude Code 项目上下文，新会话自动加载完整工作流 |
| **5 个 Skill** | deep-research / academic-paper / academic-paper-reviewer / academic-pipeline / academic-writing |
| **定时任务** | 工作日 9:00 自动写作打卡提醒 |

## 快速开始

### 1. 启动网页工具
```bash
# Windows: 双击 start-server.bat
# 或手动:
python -m http.server 8765
# 浏览器打开: http://localhost:8765/index.html
```

### 2. 配置 Claude Code
```bash
# 复制配置文件
cp .claude/settings.local.json.example .claude/settings.local.json
# 编辑 settings.local.json，根据你的环境调整权限
```

### 3. 安装 ARS Skills

ARS (Academic Research Skills) 提供 32+ Agent 的完整学术研究管线。

**首次使用自动安装**：在新 Claude Code 会话中，系统会根据 `CLAUDE.md` 自动提示安装。

**手动安装**：
```bash
git clone https://github.com/Imbad0202/academic-research-skills.git ~/academic-research-skills
cp -r ~/academic-research-skills/deep-research .claude/skills/deep-research
cp -r ~/academic-research-skills/academic-paper .claude/skills/academic-paper
cp -r ~/academic-research-skills/academic-paper-reviewer .claude/skills/academic-paper-reviewer
cp -r ~/academic-research-skills/academic-pipeline .claude/skills/academic-pipeline
```

## 10 阶段写作管线

```
选题 → 文献检索 → 大纲框架 → 引言背景 → 方法数据
→ 结果图表 → 讨论结论 → 摘要标题 → 润色降重 → 终稿投稿

     🔒 诚信闸门 2.5             🔒 诚信闸门 4.5
```

### BRTR 提示词框架

每次 AI 交互遵循：**B**ackground（背景）+ **R**ole（角色）+ **T**ask（任务）+ **R**equest（要求）

### 三角色模拟
- **作者模式**：优化表达，保持个人风格
- **审稿人模式**：逻辑/方法/表述全面审阅，0-10 评分
- **魔鬼代言人**：反谄媚协议，1-5 严重度，仅 ≥4 必须修改

### 诚信闸门（Nature 2026 七类 AI 失败模式）
引用幻觉、数据捏造、方法论造假、实施错误、幻觉结果、取巧特征、框架锁定

## 工具生态（按阶段）

| 阶段 | 推荐工具 |
|------|---------|
| 选题 | Elicit, Consensus, CNKI AI, Undermind, 秘塔AI |
| 文献 | Zotero+GPT, Semantic Scholar, ChatPDF, Research Rabbit, Connected Papers |
| 大纲 | Claude 200K, ChatGPT o1, Whimsical |
| 引言 | Claude Opus, DeepL Write |
| 方法 | ChatGPT Code Interpreter, ARS Experiment Agent |
| 结果 | Claude SVG, Napkin AI |
| 讨论 | Claude Opus, Consensus, ARS Devil's Advocate |
| 摘要 | Paperpal, Quillbot |
| 润色 | Grammarly, DeepL Write, GPTZero, Wordtune |
| 投稿 | LaTeX/Overleaf, ARS Paper Reviewer |

## 目录结构

```
.
├── CLAUDE.md                   # Claude Code 项目上下文
├── index.html   # 网页版写作工具
├── start-server.bat            # Windows 一键启动
├── README.md
├── .gitignore
└── .claude/
    ├── launch.json             # 预览服务器配置
    ├── settings.local.json.example  # 权限配置模板
    └── skills/
        ├── deep-research/      # 13 Agent 研究团队
        ├── academic-paper/     # 12 Agent 写作团队
        ├── academic-paper-reviewer/  # 7 Agent 审稿团队
        ├── academic-pipeline/  # 10 阶段全流程编排
        └── academic-writing/   # 项目定制写作助手
```

## 依赖

- [Claude Code](https://claude.ai/code) — AI 编程助手
- [ARS](https://github.com/Imbad0202/academic-research-skills) — 学术研究技能包（CC-BY-NC 4.0）
- Python 3.x（用于本地 HTTP 服务器）
- 现代浏览器（Chrome / Edge / Firefox）

## 许可

本项目的原创部分（index.html、CLAUDE.md、academic-writing skill）采用 MIT 许可。

ARS 技能包版权归 [Cheng-I Wu](https://github.com/Imbad0202) 所有，采用 CC-BY-NC 4.0 许可。
