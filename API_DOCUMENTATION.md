# 数智食堂 API 文档

> 来源：https://docs.apipost.net/docs/detail/5a305500f852000?target_id=22f3b84df6444b
> 更新时间：2026-01-15

## Base URL

```
https://api.shian360.com/order_tool/
```

## 认证方式

- ⚠️ **重要发现**：认证是通过 **Session/Cookie** 保持的
- 登录成功后，后续请求需要携带同一个 Session
- `access_token` 字段仅供参考，实际鉴权靠 Cookie

---

## 1. 登录接口

| 项目 | 内容 |
|------|------|
| **URL** | `POST /login.php?op=set` |
| **Content-Type** | `application/x-www-form-urlencoded` |

### 请求参数 (Body)

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| username | 是 | string | 手机号 |
| password | 是 | string | 密码 |

### 测试账号

| 类型 | 账号 | 密码 | 说明 |
|------|------|------|------|
| 学校 | 13956981234 | cqq.123456 | purchaser |
| 配送商 | 18805320001 | cqq.123456 | supplier |

### 响应示例

```json
{
  "code": 0,
  "data": {
    "access_token": "NWY2ZmUyZjA0M2NmYjcxMjczMzVjMWZmMjY0MmMxMDc=",
    "type": "purchaser",
    "user_id": "49",
    "genus_id": "27",
    "name": "实验小学"
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 0=成功, 1=失败 |
| data.access_token | string | 登录凭证，其他操作需要通过POST方式带上此参数 |
| data.type | string | 账号类型：`purchaser`=学校, `supplier`=配送商 |
| data.user_id | string | 登录账号ID |
| data.genus_id | string | 登录角色ID（学校ID或配送商ID） |
| data.name | string | 角色名称 |

---

## 2. 退出登录

| 项目 | 内容 |
|------|------|
| **URL** | `POST /login.php?op=out` |

### 请求参数

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| op | 是 | string | 固定值 `out` |

---

## 3. 学校列表（配送商登录后使用）

| 项目 | 内容 |
|------|------|
| **URL** | `GET /index.php?op=purchaser_list` |

### 请求参数

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| op | 是 | string | 固定值 `purchaser_list` |

### 响应示例

```json
{
  "code": 0,
  "list": [
    { "id": "770", "name": "测试" },
    { "id": "712", "name": "石练小学测试" },
    { "id": "27", "name": "实验小学" }
  ]
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 0=成功, 1=失败 |
| list | array | 学校列表 |
| list.id | string | 学校ID |
| list.name | string | 学校名称 |

---

## 4. 配送商列表（学校登录后使用）

| 项目 | 内容 |
|------|------|
| **URL** | `GET /index.php?op=supplier_list` |

### 请求参数

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| op | 是 | string | 固定值 `supplier_list` |

### 响应示例

```json
{
  "code": 0,
  "list": [
    { "id": "624", "name": "丽水市小牛餐饮管理有限公司" },
    { "id": "354", "name": "丽水大山商品有限公司" },
    { "id": "3", "name": "青岛鑫康裕蔬菜食品配送有限公司" }
  ]
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 0=成功, 1=失败 |
| list | array | 配送商列表 |
| list.id | string | 配送商ID |
| list.name | string | 配送商名称 |

---

## 5. 订单类型

| 项目 | 内容 |
|------|------|
| **URL** | `GET /index.php?op=order_type&purchaser_id=27` |

### 请求参数

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| op | 是 | string | 固定值 `order_type` |
| purchaser_id | 否 | string | 学校ID（学校登录可不传） |

### 响应示例

```json
{
  "code": 0,
  "data": [
    { "id": "11", "name": "学生营养餐" },
    { "id": "76", "name": "学生和教职工用餐" },
    { "id": "364", "name": "教职工用餐" },
    { "id": "501", "name": "学生一蛋一奶" },
    { "id": "728", "name": "其他" }
  ]
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 0=成功, 1=失败 |
| data | array | 订单类型列表 |
| data.id | string | 订单类型ID |
| data.name | string | 订单类型名称 |

---

## 6. 餐厅列表

| 项目 | 内容 |
|------|------|
| **URL** | `GET /index.php?op=warehouse&purchaser_id=1164` |

### 请求参数

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| op | 是 | string | 固定值 `warehouse` |
| purchaser_id | 是 | string | 学校ID（学校登录可不传） |

### 响应示例

```json
{
  "code": 0,
  "data": [
    { "id": "3", "name": "学生餐厅" },
    { "id": "728", "name": "教师餐厅" }
  ]
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 0=成功, 1=失败 |
| data | array | 餐厅列表 |
| data.id | string | 餐厅ID |
| data.name | string | 餐厅名称 |

---

## 7. 商品列表

| 项目 | 内容 |
|------|------|
| **URL** | `GET /index.php?op=goods&purchaser_id=27&supplier_id=3` |

### 请求参数

| 参数名 | 必填 | 类型 | 说明 |
|--------|------|------|------|
| op | 是 | string | 固定值 `goods` |
| purchaser_id | 否* | string | 学校ID（**配送商登录必填**） |
| supplier_id | 否* | string | 配送商ID（**学校登录必填**） |

### 响应示例

```json
{
  "code": 0,
  "count": 1531,
  "data": [
    {
      "goods_id": "84524",
      "cloud_id": "16",
      "code": "10877",
      "name": "大白菜",
      "letter": "dbc",
      "simple_name": "",
      "spec": "新鲜一级",
      "defaultunit": "斤",
      "unit": "斤",
      "unit_id": "unit",
      "subunit": "",
      "subunit_ratio": "0.000",
      "subunit2": "",
      "subunit2_ratio": "0.000",
      "price": "2.30"
    }
  ]
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| code | number | 0=成功, 1=失败 |
| count | number | 明细记录总数 |
| data | array | 商品列表 |
| data.goods_id | string | 配送商商品ID |
| data.cloud_id | string | 云商品ID |
| data.code | string | 商品编码 |
| data.name | string | 商品名称 |
| data.letter | string | 拼音首字母 |
| data.simple_name | string | 商品简称 |
| data.spec | string | 规格 |
| data.defaultunit | string | 默认单位 |
| data.unit | string | 单位 |
| data.unit_id | string | 单位ID |
| data.subunit | string | 辅单位 |
| data.subunit_ratio | string | 辅单位比例（与unit的比例） |
| data.subunit2 | string | 辅单位2 |
| data.subunit2_ratio | string | 辅单位2比例（与unit的比例） |
| data.price | string | 价格 |

---

## 用户类型说明

| 类型 | 值 | 说明 | 登录后可获取 |
|------|-----|------|-------------|
| 学校 | `purchaser` | 采购方 | 配送商列表、订单类型、餐厅列表 |
| 配送商 | `supplier` | 供应商 | 学校列表 |

---

## Mock 地址汇总

| 接口 | Mock URL |
|------|----------|
| 登录 | https://mock.apipost.net/mock/2b4732835865003/order_tool/login.php?apipost_id=21be7cf3b64063 |
| 退出登录 | https://mock.apipost.net/mock/2b4732835865003/order_tool/login.php?apipost_id=21c0cbf936418f |
| 学校列表 | https://mock.apipost.net/mock/2b4732835865003/order_tool/index.php?apipost_id=21c1a598b641bc |
| 配送商列表 | https://mock.apipost.net/mock/2b4732835865003/order_tool/index.php?apipost_id=22c3ebac36417c |
| 订单类型 | https://mock.apipost.net/mock/2b4732835865003/order_tool/index.php?apipost_id=22c466357641ae |
| 餐厅列表 | https://mock.apipost.net/mock/2b4732835865003/order_tool/index.php?apipost_id=22f3b84df6444b |
| 商品列表 | https://mock.apipost.net/mock/2b4732835865003/order_tool/index.php?apipost_id=22c8fcf7764251 |

---

## 待补充接口

- [ ] 提交订单
- [ ] 订单历史
- [ ] 其他...

---

## 🧪 API 测试结果 (2026-01-15)

### 学校账号登录测试
```
账号: 13956981234 / cqq.123456
登录响应: type=purchaser, genus_id=27, name=实验小学
```

**获取到的数据：**
| 接口 | 数量 | 示例 |
|------|------|------|
| 配送商列表 | 4 | 丽水市小牛餐饮管理有限公司、丽水大山商品有限公司... |
| 订单类型 | 5 | 学生营养餐、学生和教职工用餐、教职工用餐... |
| 餐厅列表 | 2 | 学生餐厅、教师餐厅 |
| 商品列表(supplier_id=3) | 504 | 大白菜、早白菜、奶白菜... |

### 配送商账号登录测试
```
账号: 18805320001 / cqq.123456
登录响应: type=supplier, genus_id=3, name=青岛鑫康裕蔬菜食品配送有限公司
```

**获取到的数据：**
| 接口 | 数量 | 示例 |
|------|------|------|
| 学校列表 | 3 | 测试、石练小学测试、实验小学 |

---

## 🔄 系统改造计划

### 第一阶段：用户认证系统

**需要新增：**
1. 登录页面 (`/login`)
2. 用户状态管理 (Zustand store)
3. 后端代理层（转发请求到远端 API，保持 Session）

**用户状态结构：**
```typescript
interface UserState {
  isLoggedIn: boolean;
  accessToken: string;
  userType: 'purchaser' | 'supplier';
  userId: string;
  genusId: string;  // 学校ID 或 配送商ID
  name: string;     // 学校名称 或 配送商名称
}
```

### 第二阶段：数据动态加载

**替换 Mock 数据：**

| 当前 Mock | 远端 API | 加载时机 |
|-----------|----------|----------|
| MOCK_CLIENTS | supplier_list / purchaser_list | 登录后根据用户类型 |
| MOCK_RESTAURANTS | warehouse | 登录后 |
| MOCK_ORDER_TYPES | order_type | 登录后 |

### 第三阶段：商品库同步 + 向量化

**流程：**
```
用户登录
  ↓
根据用户类型获取可选的"对方"列表（学校选配送商/配送商选学校）
  ↓
用户选择后，调用 goods 接口获取商品列表
  ↓
实时向量化商品库（后端）
  ↓
前端可以使用商品匹配功能
```

**技术要点：**
- 商品库按 `(purchaser_id, supplier_id)` 组合缓存
- 向量化使用现有的 embedding 服务
- 首次加载可能需要 loading 提示

### 第四阶段：订单提交对接

（等待提交订单接口文档）

---

## 🤔 待确认问题

1. **登录页 UI 设计**：简洁登录框 or 带品牌的完整页面？
2. **Session 管理**：后端代理转发 or 前端直连？
3. **商品库向量化策略**：全量一次性 or 增量/懒加载？
4. **偏好存储**：继续本地 or 迁移到远端？

