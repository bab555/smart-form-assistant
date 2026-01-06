# Docker 部署指南

本项目支持使用 Docker Compose 一键部署，包含前端（Nginx 托管）和后端（FastAPI）。

## 1. 准备工作

### 获取代码
如果你是通过 Git 拉取的代码，直接进入项目根目录：
```bash
git clone https://github.com/bab555/smart-form-assistant.git
cd smart-form-assistant
```

### 配置 API Key
由于 API Key 是敏感信息，默认配置文件名为 `.env.example`。你需要将其重命名为 `.env` 才能生效。

**操作步骤：**
1. 进入 `backend` 目录
2. 将 `.env.example` 复制或重命名为 `.env`

**Windows (PowerShell):**
```powershell
cd backend
cp .env.example .env
cd ..
```

**Linux / Mac:**
```bash
cd backend
cp .env.example .env
cd ..
```

> **注意**：`.env.example` 中已经包含了可用的阿里云 API Key，直接复制即可使用，无需修改内容。

## 2. 启动服务

在项目根目录下，运行以下命令：

```bash
docker-compose up --build -d
```

该命令会自动执行以下操作：
1. 构建后端镜像（基于 Python 3.12，安装依赖）
2. 构建前端镜像（基于 Node.js 编译，Nginx 托管）
3. 启动并编排两个容器

## 3. 访问应用

启动完成后，打开浏览器访问：

**http://localhost**

* 前端页面：80 端口
* 后端 API：内部自动代理到 8000 端口，无需单独访问

## 4. 常用命令

* **停止服务**：
  ```bash
  docker-compose down
  ```
* **查看日志**：
  ```bash
  docker-compose logs -f
  ```
* **重新构建**（当代码有更新时）：
  ```bash
  docker-compose up --build -d
  ```

