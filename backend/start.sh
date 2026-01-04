#!/bin/bash

# 智能表单助手后端启动脚本

echo "========================================="
echo "  智能表单助手 - 后端启动脚本"
echo "========================================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python3.12 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
    echo "请编辑 .env 文件，填入阿里云凭证"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip list | grep -q fastapi
if [ $? -ne 0 ]; then
    echo "❌ 依赖未安装，请先运行: pip install -r requirements.txt"
    exit 1
fi

# 检查数据目录
if [ ! -d "data" ]; then
    echo "📁 创建数据目录..."
    mkdir -p data
fi

# 检查日志目录
if [ ! -d "logs" ]; then
    echo "📁 创建日志目录..."
    mkdir -p logs
fi

# 检查向量索引
if [ ! -f "data/vector_store.index" ]; then
    echo "🔍 向量索引不存在，正在初始化..."
    python scripts/init_mock_data.py
    if [ $? -ne 0 ]; then
        echo "❌ 初始化失败"
        exit 1
    fi
fi

# 启动服务
echo ""
echo "========================================="
echo "🚀 启动服务..."
echo "========================================="
python main.py

