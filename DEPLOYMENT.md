# 学术论文写作指挥中心 — 云端部署设计文档

> 文档版本：v1.1 | 2026-06-12 | 作者：李良艳

---

## 一、项目概述

**学术论文写作指挥中心（Academic Writing Command Center）** 是一套面向管理科学博士论文写作的全流程辅助工具。核心技术形态为纯静态单页 Web 应用（SPA），内联 HTML + CSS + JavaScript，零后端依赖。

### 核心功能

| 模块 | 说明 |
|------|------|
| 10 阶段论文写作管线 | 选题 → 文献 → 大纲 → 引言 → 方法 → 结果 → 讨论 → 摘要 → 润色 → 投稿 |
| BRTR 提示词构建器 | Background / Role / Task / Request 四要素结构化提示词生成 |
| 工具推荐面板 | 按阶段推荐 AI 工具（Elicit、Zotero、Semantic Scholar 等 30+ 工具） |
| 角色模拟系统 | 作者模式 / 审稿人模式 / 魔鬼代言人三种视角切换 |
| 诚信质量闸门 | 基于 Nature 2026 的 7 类 AI 失败模式检查清单 |

### 技术栈

- 纯 HTML5 + CSS3 + Vanilla JavaScript（无框架）
- 本地开发服务器：Python 3.x `http.server`
- 版本管理：Git，双远程仓库（Gitee 主仓库 + GitHub 部署仓库）
- 云端部署：GitHub Pages

---

## 二、架构设计

### 2.1 部署架构

```
┌──────────────────────┐
│  index.html (853 行) │  ← 单文件，内联 CSS/JS
└──────────┬───────────┘
           │ git push
           ▼
┌──────────────────────┐
│  GitHub Pages        │  ← 自动 HTTPS + 全球 CDN
│  (免费，永久有效)     │
└──────────┬───────────┘
           │ 自动生成域名
           ▼
┌──────────────────────────────────────┐
│  lillianwork.github.io/              │
│    paper-writing-assistant/          │  ← 公网访问，任何人可打开
└──────────────────────────────────────┘
```

**生产环境 URL**：https://lillianwork.github.io/paper-writing-assistant/

### 2.2 Git 仓库双远程配置

```
origin  → https://gitee.com/lillian520/study.git      (主仓库，日常开发)
github  → https://github.com/lillianwork/paper-writing-assistant.git  (部署仓库)
```

日常开发推送 Gitee，需更新线上时同步推送 GitHub：

```bash
git push origin master   # 推送 Gitee
git push github master   # 推送 GitHub（自动触发 Pages 更新）
```

### 2.3 文件结构

```
study/
├── index.html                  # 主应用（入口文件）
├── CLAUDE.md                   # Claude Code 项目上下文
├── README.md                   # 项目说明
├── DEPLOYMENT.md               # 本文档
├── setup.bat                   # Windows 一键安装脚本
├── start-server.bat            # Windows 本地启动脚本
├── LICENSE                     # MIT 许可
├── .gitignore
└── .claude/
    ├── launch.json             # Claude Preview 服务器配置
    ├── settings.local.json.example
    └── skills/
        ├── deep-research/
        ├── academic-paper/
        ├── academic-paper-reviewer/
        ├── academic-pipeline/
        └── academic-writing/
```

### 2.4 入口文件改造

为满足所有云平台对静态站点的约定（默认入口为 `index.html`），将原始文件名从 `academic-writing-hub.html` 重命名为 `index.html`，并同步更新了以下引用：

| 文件 | 修改内容 |
|------|---------|
| `start-server.bat` | `academic-writing-hub.html` → `index.html` |
| `setup.bat` | `academic-writing-hub.html` → `index.html` |
| `README.md` | 全部 4 处引用更新 |
| `.claude/skills/academic-writing/SKILL.md` | URL 引用更新 |

不影响本地开发：`python -m http.server 8765` 启动后浏览器自动打开 `http://localhost:8765/index.html`。

---

## 三、部署方案

### 3.1 方案选型

对比了 6 种方案后，最终选择 **GitHub Pages**：

| 方案 | 费用 | 国内访问 | 分享给他人 | 部署方式 | 结论 |
|------|------|---------|-----------|---------|------|
| **GitHub Pages** | 免费 | 可接受（稍慢） | ✅ 永久链接 | Git 推送 | ✅ **最终采用** |
| Vercel | 免费 | ❌ 不稳定 | ✅ | CLI 需登录 | ❌ 登录失败 |
| Zeabur | 收费 | ✅ 良好 | ✅ | CLI 需登录 | ❌ 国际站/中国站不互通 |
| Gitee Pages | 免费 | ✅ 好 | ✅ | Git 推送 | ❌ 需实名认证 |
| EdgeOne Pages | 免费 | ✅ 优秀 | ❌ 鉴权限制 | 网页直传 | ❌ 预览链接仅本人可打开 |
| Cloudflare Pages | 免费 | ❌ 不稳定 | ✅ | Git 推送 | ❌ 国内部分被干扰 |

### 3.2 部署流程

**前置条件**：GitHub 账号（https://github.com ）

**第一步：创建 GitHub 仓库**

打开 https://github.com/new ，创建公开仓库（如 `paper-writing-assistant`），**不要**勾选「Add a README file」。

**第二步：配置双远程推送**

```bash
cd study
git remote add github https://github.com/<用户名>/<仓库名>.git
git push github master
```

**第三步：开启 GitHub Pages**

打开仓库 Settings → Pages：
- Source：`Deploy from a branch`
- Branch：`master`，目录 `/ (root)`
- 点击 Save

30 秒后部署完成，获得永久地址：

```
https://<用户名>.github.io/<仓库名>/
```

### 3.3 后续更新

修改代码后重新部署：

```bash
git add -A
git commit -m "..."
git push github master
```

推送后 GitHub Pages 自动重建（约 30-60 秒生效），无需手动操作。

### 3.4 GitHub Pages 限制说明

| 项目 | 限制 |
|------|------|
| 单文件大小 | 最大 1GB |
| 站点总大小 | 最大 1GB（published） |
| 每月流量 | 100GB（软限制） |
| 每小时构建 | 最多 10 次 |
| 自定义域名 | 支持（需在仓库中添加 CNAME 文件） |

本项目约 40KB，远低于所有限制。

### 3.5 EdgeOne Pages 经验教训

最初部署到腾讯 EdgeOne Pages 遇到了两个致命问题：

1. **3 小时有效期**：免费预览链接仅 3 小时有效，过期返回 401
2. **鉴权绑定登录态**：即使链接未过期，也只能在登录了腾讯云的浏览器中打开，分享给他人立即 401

EdgeOne Pages 的预览链接本质是**开发者预览**用途，不适合公开分享。如需正式使用，必须绑定已备案的自定义域名。对于无需备案的免费公网分享场景，GitHub Pages 是更合适的选择。

---

## 四、双环境运维

### 本地开发环境

```bash
cd study
python -m http.server 8765
# 访问 http://localhost:8765/index.html
```

双击 `start-server.bat` 一键启动。

### 生产环境（GitHub Pages）

- 访问地址：https://lillianwork.github.io/paper-writing-assistant/
- 更新方式：`git push github master`，自动部署
- 构建日志：仓库 Settings → Pages 页面查看

---

## 五、安全与限制

- **无后端服务**：所有数据存储在浏览器本地（localStorage），不上传服务器
- **HTTPS 强制**：GitHub Pages 自动启用 HTTPS
- **公开仓库**：代码对所有人可见（如需私有仓库，GitHub Pages 需付费）

---

## 六、方案评审记录

| 日期 | 方案 | 结果 | 原因 |
|------|------|------|------|
| 2026-06-12 | Vercel CLI | ❌ 失败 | npm 安装缓慢，登录认证超时 |
| 2026-06-12 | Gitee Pages | ❌ 失败 | Pages 设置页 404，需公开仓库 + 实名 |
| 2026-06-12 | Zeabur CLI | ❌ 失败 | zeabur.com 与 zeabur.cn 账户不互通 |
| 2026-06-12 | EdgeOne Pages | ❌ 失败 | 部署成功但预览链接鉴权绑定登录态，无法分享 |
| 2026-06-12 | **GitHub Pages** | ✅ **成功** | Git 推送部署，永久公开链接，完全免费 |

---

*本文档由 AI 辅助生成，内容基于实际部署验证结果。*
