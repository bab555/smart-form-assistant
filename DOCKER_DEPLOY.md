# 🐳 Docker 部署指南

本指南将帮助你使用 Docker 快速部署 **智能订单助手**。

## 前置要求

- Docker (20.10+)
- Docker Compose (v2.0+)

## 🚀 快速启动

### 1. 配置环境变量

首先，复制示例配置文件：

```bash
cd backend
cp .env.example .env
```

然后编辑 `.env` 文件，填入必要的 API Key（阿里云 Qwen）：

```ini
# .env 文件
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 2. 启动服务

在项目根目录下执行：

```bash
# 构建并启动（后台运行）
docker-compose up --build -d
```

### 3. 访问应用

- **前端页面**: http://localhost
- **后端 API**: http://localhost:8000/docs

---

## 📂 数据持久化

Docker 配置中已预设了数据卷挂载，以下数据会持久化保存在宿主机项目目录下：

| 宿主机目录 | 容器内路径 | 说明 |
|-----------|------------|------|
| `./data/` | `/app/data/` | 向量数据库索引、用户偏好设置 |
| `./uploads/` | `/app/uploads/` | 上传的文件 |

**注意**：请定期备份 `./data` 目录。

---

## 🛠️ 常用命令

```bash
# 查看日志
docker-compose logs -f

# 查看日志 (只看后端)
docker-compose logs -f backend

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 清理所有数据（慎用！）
docker-compose down -v
```

## 🔄 更新部署

当你修改了代码后，执行以下命令重新构建并启动：

```bash
docker-compose up --build -d
```
