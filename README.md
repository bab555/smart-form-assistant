# 🤖 智能订单助手 (Smart Order Assistant)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](DOCKER_DEPLOY.md)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](backend/)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB.svg)](frontend/)

**智能订单助手**是一个基于 AI 驱动的多模态智能订单识别系统。它能够通过语音、图片、文档等多种方式接收输入，利用大语言模型（Qwen）和 AI Agent 技术自动提取、校准并填充结构化表格，极大地提高了订单处理效率和准确性。

## ✨ 核心特性

- **📷 多模态识别**：
  - **OCR**: 支持图片、PDF、扫描件的文字提取。
  - **文档解析**: 直接解析 Excel、Word、PPT 等格式。
  - **手写识别**: 针对手写表单进行专门优化。
- **🎙️ 语音指令**：
  - 实时语音识别（ASR）。
  - 自然语言命令执行（如“把第一行的数量改为 50”）。
- **🧠 智能 Agent**：
  - **LangGraph 工作流**: 编排复杂的认知任务（OCR -> 分析 -> 提取 -> 校准 -> 填充）。
  - **知识库校准**: 基于向量数据库（FAISS）自动修正错别字、标准化术语（如将“红富土”校准为“红富士”）。
  - **歧义处理**: 遇到不确定的内容自动标记，并提供候选词供用户选择。
- **🎨 实时可视化**：
  - 沉浸式 UI 展示 AI 的“思维过程”。
  - 实时反馈任务进度和系统日志。

## 🏗️ 系统架构

项目采用前后端分离架构：

*   **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
    *   Nginx 托管，内置反向代理。
*   **Backend**: Python 3.12 + FastAPI + LangGraph + DashScope SDK
    *   集成阿里云通义千问（Qwen-Max, Qwen-VL, Qwen-Turbo）。

## 🚀 快速启动 (Docker 部署)

这是最简单的运行方式，适合部署或快速体验。

### 1. 获取代码
```bash
git clone https://github.com/bab555/smart-form-assistant.git
cd smart-form-assistant
```

### 2. 配置密钥
```bash
cd backend
cp .env.example .env
# .env.example 中已包含可用 Key，直接复制即可
cd ..
```

### 3. 一键运行
```bash
docker-compose up --build -d
```

启动后访问：**http://localhost**

> 详细部署说明请参考 [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)

## 💻 本地开发

如果你需要修改代码，可以分别启动前后端开发环境。

### 后端 (Backend)
```bash
cd backend
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
# 2. 安装依赖
pip install -r requirements.txt
# 3. 运行
python main.py
```
*API 文档*: http://localhost:8000/docs

### 前端 (Frontend)
```bash
cd frontend
# 1. 安装依赖
npm install
# 2. 运行
npm run dev
```
*访问地址*: http://localhost:3000

## 📂 目录结构

*   `backend/`: 后端服务代码
    *   `app/agents/`: LangGraph 工作流定义
    *   `app/services/`: LLM、OCR、文档服务封装
    *   `Dockerfile`: 后端镜像构建文件
*   `frontend/`: 前端应用代码
    *   `src/components/visualizer/`: 流程可视化组件
    *   `Dockerfile`: 前端镜像构建文件
*   `docker-compose.yml`: 容器编排配置
*   `DOCKER_DEPLOY.md`: 部署文档

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

