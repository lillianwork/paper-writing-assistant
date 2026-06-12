# 学术论文写作指挥中心 — 云端部署设计文档

> 文档版本：v1.0 | 2026-06-12 | 作者：李良艳

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
- 版本管理：Git + Gitee 远程仓库
- 云端部署：腾讯 EdgeOne Pages

---

## 二、架构设计

### 2.1 部署架构

```
┌──────────────────────┐
│  index.html (853 行) │  ← 单文件，内联 CSS/JS
└──────────┬───────────┘
           │ 上传
           ▼
┌──────────────────────┐
│  腾讯 EdgeOne Pages  │  ← 全球 3200+ 边缘节点
│  (免费不限流量)       │
└──────────┬───────────┘
           │ 自动分配域名
           ▼
┌──────────────────────┐
│  xxxxx.edgeone.app   │  ← 公网访问（自动 HTTPS）
└──────────────────────┘
```

### 2.2 文件结构

```
study/
├── index.html                  # 主应用（入口文件）
├── CLAUDE.md                   # Claude Code 项目上下文
├── README.md                   # 项目说明
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

### 2.3 入口文件改造

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

对比了 5 种方案后选择腾讯 EdgeOne Pages：

| 方案 | 费用 | 国内访问 | 部署方式 | 结论 |
|------|------|---------|---------|------|
| **EdgeOne Pages** | 免费 | ✅ 优秀 | 网页直传 | ✅ 采用 |
| Vercel | 免费 | ❌ 不稳定 | CLI 需登录 | ❌ 登录失败 |
| Zeabur | 收费 | ✅ 良好 | CLI 需登录 | ❌ 国际站/中国站不互通 |
| Gitee Pages | 免费 | ✅ 好 | Git 推送 | ❌ 需实名认证，入口 404 |
| GitHub Pages | 免费 | ❌ 慢 | Git 推送 | ❌ 国内访问慢 |

### 3.2 部署流程

**第一步：登录腾讯云**

打开 https://console.cloud.tencent.com/edgeone/pages ，使用微信扫码或腾讯云账号登录。无账号可直接用微信注册。

**第二步：创建项目**

点击「创建项目」→ 选择「直接上传」→ 将 `index.html` 拖入上传区域。

**第三步：部署**

点击「开始部署」，约 30 秒完成。系统自动分配域名：

```
https://<项目名>-<随机ID>.edgeone.app
```

**无需任何额外配置**：自动 HTTPS、自动 CDN、自动压缩。

### 3.3 后续更新

每次修改 `index.html` 后更新云端：

1. **网页端**：进入项目 →「上传新版本」→ 重新上传文件
2. **未来可选**：绑定 Gitee 仓库实现 `git push` 自动部署（需配置构建命令为空、输出目录为根目录）

### 3.4 自定义域名（可选）

如需使用自己的域名：

1. EdgeOne Pages 项目设置 → 域名管理 → 添加自定义域名
2. 在 DNS 提供商添加 CNAME 记录指向 EdgeOne 提供的地址
3. 若选择「含中国大陆」加速，域名需 ICP 备案

### 3.5 已知限制：预览链接 3 小时过期

EdgeOne Pages 系统生成的免费预览域名（`*.edgeone.app`）存在 **3 小时有效期限制**。过期后访问返回 401 UNAUTHORIZED。

**临时解决**：进入项目概览 → 点击「预览」按钮，生成新链接。

**永久解决**（三选一）：

| 方案 | 操作 | 说明 |
|------|------|------|
| 绑定自定义域名 | 项目设置 → 域名管理 → 添加域名 | 需 ICP 备案，但一劳永逸 |
| 切换加速区域 | 新建项目，加速区域选「全球（不含中国大陆）」 | 无需备案，但国内直接访问受限（需 VPN/境外网络） |
| 定期刷新 | 每 3 小时手动点击「预览」 | 免费但繁琐，适合临时使用 |

---

## 四、双环境运维

### 本地开发环境

```bash
# 启动
cd study
python -m http.server 8765
# 浏览器访问 http://localhost:8765/index.html
```

也可双击 `start-server.bat` 一键启动。

### 生产环境（云端）

- 访问地址：EdgeOne Pages 分配的 `.edgeone.app` 域名
- 更新方式：EdgeOne 控制台上传新版本
- 监控：EdgeOne 控制台提供访问统计、带宽监控

---

## 五、安全与限制

- **无后端服务**：所有数据存储在浏览器本地（localStorage），不上传服务器
- **HTTPS 强制**：EdgeOne 自动启用 HTTPS
- **DDoS 防护**：平台级 WAF 和 DDoS 防护内置
- **文件限制**：EdgeOne 免费套餐支持单文件不超过 25MB（本项目 853 行 HTML，约 40KB，远低于限制）

---

## 六、方案评审记录

| 日期 | 方案 | 结果 | 原因 |
|------|------|------|------|
| 2026-06-12 | Vercel CLI | 失败 | npm 全局安装缓慢，登录认证超时 |
| 2026-06-12 | Gitee Pages | 失败 | Pages 设置页 404，疑似需公开仓库或实名 |
| 2026-06-12 | Zeabur CLI | 失败 | zeabur.com 与 zeabur.cn 账户体系不互通 |
| 2026-06-12 | **EdgeOne Pages** | **成功** | 网页直传，30 秒部署，国内访问流畅 |

---

*本文档由 AI 辅助生成，内容基于实际部署验证结果。*
