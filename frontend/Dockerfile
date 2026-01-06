# Build Stage
FROM node:20-alpine as builder

WORKDIR /app

# 复制 package.json 和 lock 文件
COPY package.json package-lock.json ./

# 安装依赖
RUN npm ci --registry=https://registry.npmmirror.com

# 复制源代码
COPY . .

# 构建前端应用
# 设置 VITE_API_BASE_URL 为 /api，VITE_WS_URL 为 /ws
# 这样前端请求会发给同域名的 Nginx，然后由 Nginx 转发给后端
RUN VITE_API_BASE_URL=/api VITE_WS_URL=/ws npm run build

# Production Stage
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

