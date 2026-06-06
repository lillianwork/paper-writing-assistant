@echo off
echo ============================================
echo   学术论文写作指挥中心 — 一键安装
echo ============================================
echo.

REM 1. Install ARS (Academic Research Skills)
echo [1/3] 安装 ARS 学术研究技能包...
if exist ".claude\skills\deep-research\SKILL.md" (
    echo   ARS skills 已安装，跳过。
) else (
    if not exist ".claude\plugins\academic-research-skills" (
        echo   正在克隆 ARS 仓库...
        git clone --depth 1 https://github.com/Imbad0202/academic-research-skills.git .claude\plugins\academic-research-skills
    )
    echo   复制 skill 文件...
    xcopy /E /I /Y ".claude\plugins\academic-research-skills\deep-research" ".claude\skills\deep-research" >nul
    xcopy /E /I /Y ".claude\plugins\academic-research-skills\academic-paper" ".claude\skills\academic-paper" >nul
    xcopy /E /I /Y ".claude\plugins\academic-research-skills\academic-paper-reviewer" ".claude\skills\academic-paper-reviewer" >nul
    xcopy /E /I /Y ".claude\plugins\academic-research-skills\academic-pipeline" ".claude\skills\academic-pipeline" >nul
    echo   ARS skills 安装完成。
)

REM 2. Copy settings template
echo [2/3] 配置 Claude Code 权限...
if not exist ".claude\settings.local.json" (
    copy ".claude\settings.local.json.example" ".claude\settings.local.json" >nul
    echo   已创建 settings.local.json，请根据需要编辑。
) else (
    echo   settings.local.json 已存在，跳过。
)

REM 3. Start preview server
echo [3/3] 启动预览服务器...
start http://localhost:8765/academic-writing-hub.html
python -m http.server 8765

pause
