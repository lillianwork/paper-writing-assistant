# 李良艳 — 学术论文写作工作台

## 项目概况
- **定位**：人大管科博士学位论文全流程管理
- **方向**：管理科学与工程（具体方向见选题申请表）
- **工作目录**：`F:\人大管科\李良艳的大论文`

## 核心工作流：10 阶段论文写作管线

```
阶段 1: 研究选题     → 阶段 2: 文献检索    → 阶段 3: 大纲框架
阶段 4: 引言与背景   → 阶段 5: 方法与数据  → 阶段 6: 结果与图表
阶段 7: 讨论与结论   → 阶段 8: 摘要与标题  → 阶段 9: 润色与降重
阶段 10: 终稿与投稿
```

每个阶段切换时调用 `mcp__ccd_session__mark_chapter` 标记新章节。

### 诚信闸门（不可跳过）
- **Stage 2.5**（大纲完成后）：7 类 AI 失败模式检查
- **Stage 4.5**（方法完成后）：二次验证，零回归确认

## BRTR 提示词框架

每次与 AI 交互必须使用此框架：
- **B**ackground — 研究背景、已有进展、未解决问题
- **R**ole — AI 扮演的角色（资深教授 / 期刊审稿人 / 方法论专家 / 魔鬼代言人）
- **T**ask — 具体任务描述
- **R**equest — 输出格式与约束

## 工具推荐（按阶段）

| 阶段 | 工具 |
|------|------|
| 选题 | Elicit, Consensus, CNKI AI助手, Undermind, 秘塔AI搜索 |
| 文献 | Zotero+GPT, Semantic Scholar, ChatPDF, Research Rabbit, Connected Papers, 星火科研助手 |
| 大纲 | Claude (200K), ChatGPT o1, Whimsical |
| 引言 | Claude Sonnet/Opus, DeepL Write |
| 方法 | ChatGPT Code Interpreter, Python/R + AI, Experiment Agent (ARS) |
| 结果 | Claude (SVG图表), Napkin AI |
| 讨论 | Claude Opus, Consensus, Devil's Advocate (ARS) |
| 摘要 | Paperpal, Quillbot |
| 润色 | Grammarly, DeepL Write, GPTZero, Wordtune |
| 投稿 | LaTeX/Overleaf, 知网格式精灵, Academic Paper Reviewer (ARS) |

## 角色模式

随时可通过切换角色视角审视论文：
- **👤 作者模式**：优化表达，保持个人风格
- **🔍 审稿人模式**：逻辑、方法、表述全面审阅，0-10 评分
- **😈 魔鬼代言人**：强制挑刺，1-5 严重度评分，仅 ≥4 必须修改

## 可用 MCP 工具

- `mcp__Claude_Preview__*` — 浏览器预览与调试
- `mcp__Claude_in_Chrome__*` — Chrome 浏览器自动化
- `mcp__ccd_session__*` — 章节标记与任务派生
- `mcp__ccd_directory__*` — 文件系统扩展访问
- `mcp__scheduled-tasks__*` — 定时任务管理

## 已安装 Skills（5 个）

| Skill | 触发方式 | 功能 |
|-------|---------|------|
| **deep-research** | 说"深度研究"/"文献回顾"/"系统综述" | 13 Agent 研究团队，7 种模式 |
| **academic-paper** | 说"写论文"/"帮我写引言"/"搭大纲" | 12 Agent 写作团队，10 种模式 |
| **academic-paper-reviewer** | 说"审稿"/"同行评审"/"模拟审稿" | 7 Agent 审稿团队（主编+3审稿人+魔鬼代言人） |
| **academic-pipeline** | 说"全流程"/"端到端论文"/"完整管线" | 10 阶段全流程编排器 |
| **academic-writing** | `/academic-writing` 或说"论文写作助手" | 本项目中文化工作流（BRTR 框架、角色模拟、质量闸门） |

### ARS 全流程管线

```
deep-research → academic-paper → 诚信闸门(Stage 2.5)
  → academic-paper-reviewer → academic-paper(revision)
    → 诚信闸门(Stage 4.5) → 终稿输出
```

**成本参考**：一篇 15,000 字论文约 $4-6 美元（Claude API）。

### 关键 ARS 命令

- `ars-plan` — 苏格拉底式逐章规划
- `ars-full` — 完整论文撰写
- `ars-reviewer` — 多视角同行评审
- `ars-outline` — 仅生成大纲
- `ars-revision` — 基于审稿意见修订
- `ars-abstract` — 仅写摘要
- `ars-citation-check` — 引用格式检查
- `ars-disclosure` — 生成 AI 使用声明
- `ars-format-convert` — 格式转换（LaTeX/IEEE/APA）
