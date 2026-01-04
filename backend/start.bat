@echo off
REM 智能表单助手后端启动脚本 (Windows)

echo =========================================
echo   智能表单助手 - 后端启动脚本
echo =========================================

REM 检查虚拟环境
if not exist "venv" (
    echo ❌ 虚拟环境不存在，请先运行: python3.12 -m venv venv
    exit /b 1
)

REM 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查环境变量
if not exist ".env" (
    echo ⚠️  .env 文件不存在，从 .env.example 复制...
    copy .env.example .env
    echo 请编辑 .env 文件，填入阿里云凭证
    exit /b 1
)

REM 检查数据目录
if not exist "data" (
    echo 📁 创建数据目录...
    mkdir data
)

REM 检查日志目录
if not exist "logs" (
    echo 📁 创建日志目录...
    mkdir logs
)

REM 检查向量索引
if not exist "data\vector_store.index" (
    echo 🔍 向量索引不存在，正在初始化...
    python scripts\init_mock_data.py
    if errorlevel 1 (
        echo ❌ 初始化失败
        exit /b 1
    )
)

REM 启动服务
echo.
echo =========================================
echo 🚀 启动服务...
echo =========================================
python main.py

