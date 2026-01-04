# 智能表单助手 - 后端系统

## 🚀 快速启动

### 1. 创建虚拟环境
```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入阿里云凭证
```

### 4. 初始化数据
```bash
python scripts/init_mock_data.py
```

### 5. 启动服务
```bash
# 开发模式（自动重载）
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📁 项目结构

```
backend/
├── app/
│   ├── api/              # API 路由
│   ├── core/             # 核心配置
│   ├── services/         # 阿里云服务封装
│   ├── agents/           # LangGraph Agent
│   ├── models/           # 数据模型
│   └── utils/            # 工具函数
├── data/                 # 向量数据库文件
├── logs/                 # 日志文件
├── scripts/              # 初始化脚本
├── main.py               # 应用入口
└── requirements.txt      # 依赖列表
```

## 🔗 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 测试

```bash
pytest tests/ -v
```

