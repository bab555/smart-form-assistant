# 使用官方 Python 3.12 轻量级镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  # 设置时区为上海
  TZ=Asia/Shanghai

# 安装系统依赖
# build-essential: 编译依赖
# libgl1: 图像处理通用依赖 (OpenCV/Pillow 等可能需要)
# 安装系统依赖
# build-essential: 编译依赖
# libgl1: 图像处理通用依赖 (OpenCV/Pillow 等可能需要)
# 替换为阿里源加速
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
  && apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  libgl1 \
  libglib2.0-0 \
  poppler-utils \
  && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
  && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# 使用清华源加速下载
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/uploads /app/data /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "main:app", "--workers", "1", "--threads", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "300", "--keep-alive", "65", "--max-requests", "1000", "--max-requests-jitter", "50"]
