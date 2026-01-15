# 远端 API 集成改造计划

> 创建时间：2026-01-15
> 状态：待实施

## 📋 需求确认

| 项目 | 决定 |
|------|------|
| 提交订单接口 | ⏸️ 暂不对接，留好校验和接口预留 |
| 商品库同步时机 | ✅ 登录后立即同步并向量化 |
| 同步提示 | ✅ 前端显示"正在同步资料..." |
| 记住登录 | ✅ 需要实现 |
| 登录页设计 | ✅ 与网站风格一致，无验证码 |

---

## 🏗️ 架构设计

### 整体流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户登录流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   前端登录页 ──POST──▶ 后端代理 ──POST──▶ 远端API                 │
│        │                  │                  │                  │
│        │              保存Session            │                  │
│        │                  │                  │                  │
│        ◀──返回用户信息────◀──返回用户信息────◀                   │
│        │                                                        │
│   保存到 localStorage (记住登录)                                 │
│        │                                                        │
│   显示"正在同步资料..."                                          │
│        │                                                        │
│   请求商品库 ──GET──▶ 后端代理 ──GET──▶ 远端API                  │
│        │                  │                  │                  │
│        │              向量化商品库            │                  │
│        │                  │                  │                  │
│        ◀──完成通知────────◀                                     │
│        │                                                        │
│   进入主应用                                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 后端代理层设计

```
backend/app/api/
├── endpoints.py          # 现有
├── websocket.py          # 现有
└── remote_api.py         # 新增：远端API代理
```

**代理层职责：**
1. 管理与远端 API 的 Session
2. 转发请求并返回结果
3. 触发商品库向量化
4. 缓存用户登录状态

---

## 📁 文件改动清单

### 后端 (backend/)

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/api/remote_api.py` | 新增 | 远端 API 代理层 |
| `app/services/remote_session.py` | 新增 | Session 管理 |
| `app/services/knowledge_base.py` | 修改 | 支持动态重载商品库 |
| `main.py` | 修改 | 注册新路由 |

### 前端 (frontend/)

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/pages/Login.tsx` | 新增 | 登录页面 |
| `src/pages/Login.css` | 新增 | 登录页样式 |
| `src/store/useAuthStore.ts` | 新增 | 用户认证状态 |
| `src/store/useDataStore.ts` | 新增 | 动态数据（配送商/餐厅/订单类型） |
| `src/App.tsx` | 修改 | 路由守卫 |
| `src/components/Canvas/TableCard.tsx` | 修改 | 移除 MOCK，使用动态数据 |
| `src/components/SyncOverlay.tsx` | 新增 | 同步中遮罩层 |

---

## 🔌 后端 API 设计

### 1. 登录接口

```
POST /api/auth/login
```

**请求：**
```json
{
  "username": "13956981234",
  "password": "cqq.123456",
  "remember": true
}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "userType": "purchaser",
    "userId": "49",
    "genusId": "27",
    "name": "实验小学",
    "token": "本地生成的token用于记住登录"
  }
}
```

### 2. 检查登录状态

```
GET /api/auth/check
```

**Headers：** `Authorization: Bearer <token>`

**响应：**
```json
{
  "success": true,
  "data": { ... } // 同登录响应
}
```

### 3. 退出登录

```
POST /api/auth/logout
```

### 4. 获取配送商/学校列表

```
GET /api/data/partners
```

**响应（学校登录）：**
```json
{
  "success": true,
  "data": [
    { "id": "624", "name": "丽水市小牛餐饮管理有限公司" },
    ...
  ]
}
```

### 5. 获取餐厅列表

```
GET /api/data/restaurants
```

### 6. 获取订单类型

```
GET /api/data/order_types
```

### 7. 同步商品库

```
POST /api/data/sync_products
```

**请求：**
```json
{
  "partnerId": "3"  // 配送商ID或学校ID
}
```

**响应：**
```json
{
  "success": true,
  "message": "商品库同步完成",
  "count": 504
}
```

### 8. 提交订单（预留）

```
POST /api/order/submit
```

**请求：**
```json
{
  "restaurantId": "3",
  "orderTypeId": "11",
  "date": "2026-01-15T12:00",
  "items": [
    { "goodsId": "1419", "name": "大白菜", "quantity": 10, "unit": "斤" },
    ...
  ]
}
```

**响应（暂时）：**
```json
{
  "success": false,
  "message": "订单提交接口待对接"
}
```

---

## 🎨 前端状态设计

### useAuthStore

```typescript
interface AuthState {
  isLoggedIn: boolean;
  isLoading: boolean;
  user: {
    userType: 'purchaser' | 'supplier';
    userId: string;
    genusId: string;
    name: string;
  } | null;
  token: string | null;
  
  login: (username: string, password: string, remember: boolean) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}
```

### useDataStore

```typescript
interface DataState {
  // 合作方（学校看配送商，配送商看学校）
  partners: Array<{ id: string; name: string }>;
  selectedPartnerId: string | null;
  
  // 餐厅
  restaurants: Array<{ id: string; name: string }>;
  
  // 订单类型
  orderTypes: Array<{ id: string; name: string }>;
  
  // 同步状态
  isSyncing: boolean;
  syncMessage: string;
  
  // Actions
  loadPartners: () => Promise<void>;
  loadRestaurants: () => Promise<void>;
  loadOrderTypes: () => Promise<void>;
  syncProducts: (partnerId: string) => Promise<void>;
}
```

---

## 📐 登录页设计

**风格：** 与主应用一致（深蓝色渐变 + 白色卡片）

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    ┌──────────────────────┐                     │
│                    │      🍽️ LOGO        │                     │
│                    │                      │                     │
│                    │   智能订单助手        │                     │
│                    │                      │                     │
│                    │  ┌────────────────┐  │                     │
│                    │  │ 📱 手机号      │  │                     │
│                    │  └────────────────┘  │                     │
│                    │                      │                     │
│                    │  ┌────────────────┐  │                     │
│                    │  │ 🔒 密码        │  │                     │
│                    │  └────────────────┘  │                     │
│                    │                      │                     │
│                    │  ☑️ 记住登录         │                     │
│                    │                      │                     │
│                    │  ┌────────────────┐  │                     │
│                    │  │    登  录      │  │                     │
│                    │  └────────────────┘  │                     │
│                    │                      │                     │
│                    └──────────────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⏱️ 实施步骤

### Step 1: 后端代理层 (约 1 小时)
- [ ] 创建 `remote_api.py`
- [ ] 创建 `remote_session.py`
- [ ] 实现登录/登出接口
- [ ] 实现数据获取接口

### Step 2: 商品库动态加载 (约 30 分钟)
- [ ] 修改 `knowledge_base.py` 支持重载
- [ ] 实现同步接口

### Step 3: 前端登录页 (约 1 小时)
- [ ] 创建登录页组件
- [ ] 创建 `useAuthStore`
- [ ] 实现路由守卫

### Step 4: 前端数据动态化 (约 1 小时)
- [ ] 创建 `useDataStore`
- [ ] 移除 MOCK 数据
- [ ] 实现同步遮罩层

### Step 5: 测试联调 (约 30 分钟)
- [ ] 登录流程测试
- [ ] 数据加载测试
- [ ] 商品库同步测试

---

## ⚠️ 注意事项

1. **Session 管理**：远端 API 使用 Cookie 认证，后端需要为每个用户维护独立的 Session
2. **Token 设计**：本地 token 用于"记住登录"，与远端 access_token 分开
3. **错误处理**：网络异常、登录过期等情况需要友好提示
4. **向量化耗时**：商品库较大时（500+条）向量化可能需要几秒，需要 loading 提示

---

准备好了吗？我们开始实施！

