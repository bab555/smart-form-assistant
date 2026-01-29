"""
远端 API 代理路由

提供：
1. 登录/登出/检查登录状态
2. 获取配送商/学校列表
3. 获取餐厅列表
4. 获取订单类型
5. 同步商品库（含向量化）
6. 提交订单（预留）
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.services.remote_session import remote_session_manager
from app.services.knowledge_base import vector_store as knowledge_base
from app.core.logger import app_logger as logger

router = APIRouter()


# ========== 请求/响应模型 ==========

class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False


class SSOLoginRequest(BaseModel):
    token: str


class LoginResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class PartnerItem(BaseModel):
    id: str
    name: str


class RestaurantItem(BaseModel):
    id: str
    name: str


class OrderTypeItem(BaseModel):
    id: str
    name: str


class SyncRequest(BaseModel):
    partnerId: str


class SubmitOrderRequest(BaseModel):
    partnerId: str
    restaurantId: str
    orderTypeId: str
    date: str
    remark: Optional[str] = ""
    items: List[Dict[str, Any]]


# ========== 辅助函数 ==========

def extract_token(authorization: Optional[str]) -> Optional[str]:
    """从 Authorization header 提取 token"""
    if not authorization:
        return None
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


# ========== 认证接口 ==========

@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """用户登录"""
    result = await remote_session_manager.login(req.username, req.password)
    
    if result:
        return LoginResponse(success=True, data=result)
    else:
        return LoginResponse(success=False, message="用户名或密码错误")


@router.post("/auth/sso", response_model=LoginResponse)
async def sso_login(req: SSOLoginRequest):
    """
    SSO 登录接口
    前端 iframe 收到 token 后调用此接口
    """
    if not req.token:
        return LoginResponse(success=False, message="Token 不能为空")
        
    result = await remote_session_manager.login_by_token(req.token)
    
    if result:
        return LoginResponse(success=True, data=result)
    else:
        return LoginResponse(success=False, message="Token 验证失败或已过期")


@router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """用户登出"""
    token = extract_token(authorization)
    if token:
        await remote_session_manager.logout(token)
    return {"success": True}


@router.get("/auth/check", response_model=LoginResponse)
async def check_auth(authorization: Optional[str] = Header(None)):
    """检查登录状态"""
    token = extract_token(authorization)
    if not token:
        return LoginResponse(success=False, message="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        return LoginResponse(success=False, message="登录已过期")
    
    return LoginResponse(
        success=True,
        data={
            "userType": session.user_type,
            "userId": session.user_id,
            "genusId": session.genus_id,
            "name": session.name,
            "token": token,
        }
    )


# ========== 数据接口 ==========

@router.get("/data/partners")
async def get_partners(authorization: Optional[str] = Header(None)):
    """
    获取合作方列表
    - 学校登录：返回配送商列表
    - 配送商登录：返回学校列表
    """
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    # 根据用户类型调用不同接口
    if session.user_type == "purchaser":
        # 学校 -> 获取配送商列表
        result = await remote_session_manager.request(
            token, "POST", "/index.php", params={"op": "supplier_list"}
        )
    else:
        # 配送商 -> 获取学校列表
        result = await remote_session_manager.request(
            token, "POST", "/index.php", params={"op": "purchaser_list"}
        )
    
    logger.info(f"[Partners] user_type={session.user_type}, result={result}")
    
    if not result or result.get("code") != 0:
        return {"success": False, "data": [], "message": "获取失败"}
    
    # 解析数据
    partners = []
    # API 返回的是 list 字段，不是 data
    raw_data = result.get("list", [])
    if not raw_data:
        # 尝试兼容 data 字段
        raw_data = result.get("data", [])
    
    for item in raw_data:
        # API 直接返回 id 和 name
        partners.append({
            "id": str(item.get("id", "")),
            "name": item.get("name", ""),
        })
    
    logger.info(f"[Partners] parsed {len(partners)} items")
    return {"success": True, "data": partners}


@router.get("/data/restaurants")
async def get_restaurants(partnerId: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """获取餐厅列表"""
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    # 构造请求参数
    params = {"op": "warehouse"}
    if session.user_type == "supplier":
        # 配送商登录: 必须指定 purchaser_id (即 partnerId)
        if not partnerId:
            # 如果没传 partnerId，可能是在未选择客户的情况下调用，返回空列表而不是报错
            return {"success": True, "data": []}
        params["purchaser_id"] = partnerId
    
    result = await remote_session_manager.request(
        token, "POST", "/index.php", params=params
    )
    
    if not result or result.get("code") != 0:
        return {"success": False, "data": [], "message": "获取失败"}
    
    restaurants = []
    for item in result.get("data", []):
        restaurants.append({
            "id": str(item.get("id", "")),
            "name": item.get("name", ""),
        })
    
    return {"success": True, "data": restaurants}


@router.get("/data/order_types")
async def get_order_types(partnerId: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """获取订单类型列表"""
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    # 构造请求参数
    params = {"op": "order_type"}
    if session.user_type == "supplier":
        # 配送商登录: 必须指定 purchaser_id (即 partnerId)
        if not partnerId:
            return {"success": True, "data": []}
        params["purchaser_id"] = partnerId
    
    result = await remote_session_manager.request(
        token, "POST", "/index.php", params=params
    )
    
    if not result or result.get("code") != 0:
        return {"success": False, "data": [], "message": "获取失败"}
    
    order_types = []
    for item in result.get("data", []):
        order_types.append({
            "id": str(item.get("id", "")),
            "name": item.get("name", ""),
        })
    
    return {"success": True, "data": order_types}


from pypinyin import lazy_pinyin, Style

# ... 之前的代码 ...

# 简单的内存缓存：partner_id -> {timestamp, data}
_products_cache = {}

@router.get("/data/products")
async def get_products_list(partnerId: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """
    获取商品全量列表（带分类和拼音）
    用于前端商品选择器
    """
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
        
    # 确定目标 partnerId
    target_id = partnerId
    if session.user_type == "supplier":
        # 配送商登录，必须指定学校 ID
        if not target_id:
             return {"success": True, "data": []}
    elif session.user_type == "purchaser":
        # 学校登录，如果没有指定 partnerId，则尝试使用默认的供应商（如果有的话，或者直接返回空）
        # 这里逻辑简化：学校必须选一个供应商才能看商品
        if not target_id:
             return {"success": True, "data": []}

    # 检查缓存 (有效期 5 分钟)
    import time
    cache_key = f"{session.genus_id}_{target_id}"
    now = time.time()
    if cache_key in _products_cache:
        cached = _products_cache[cache_key]
        if now - cached["timestamp"] < 300: # 5分钟
            return {"success": True, "data": cached["data"]}

    # 调用远端 API
    params = {"op": "goods"}
    data = {}
    
    if session.user_type == "purchaser":
        data["supplier_id"] = target_id
    else:
        params["purchaser_id"] = target_id
    
    result = await remote_session_manager.request(
        token, "POST", "/index.php", 
        params=params,
        data=data
    )
    
    if not result or result.get("code") != 0:
        return {"success": False, "data": [], "message": "获取失败"}
        
    # 处理数据：添加拼音
    products = []
    for item in result.get("data", []):
        name = item.get("name", "")
        # 生成简拼 (szst) 和 全拼 (shuzhishitang)
        # lazy_pinyin 返回 ['shu', 'zhi']
        full_pinyin = "".join(lazy_pinyin(name))
        first_letters = "".join([p[0] for p in lazy_pinyin(name, style=Style.FIRST_LETTER)])
        
        products.append({
            "id": str(item.get("goods_id", "")),
            "name": name,
            "spec": item.get("spec", ""),
            "unit": item.get("unit", ""),
            "category": item.get("category_name", "") or "未分类",
            "price": item.get("price", ""),
            "pinyin": full_pinyin,
            "py": first_letters, # 简拼
        })
    
    # 写入缓存
    _products_cache[cache_key] = {
        "timestamp": now,
        "data": products
    }
    
    return {"success": True, "data": products}


@router.post("/data/sync_products")
async def sync_products(req: SyncRequest, authorization: Optional[str] = Header(None)):
    """
    同步商品库并向量化
    
    流程：
    1. 调用远端 API 获取商品列表
    2. 转换为知识库格式
    3. 重新向量化
    """
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    logger.info(f"[SyncProducts] Starting sync for partner {req.partnerId}")
    
    # 调用远端 API 获取商品列表
    params = {"op": "goods"}
    data = {}
    
    if session.user_type == "purchaser":
        # 学校登录: partnerId 是 配送商 (supplier_id)
        data["supplier_id"] = req.partnerId
    else:
        # 配送商登录: partnerId 是 学校 (purchaser_id)
        params["purchaser_id"] = req.partnerId
        # 注意：这里可能需要同时把 supplier_id 设为自己(session.genus_id)或者不传
        # 根据文档，配送商登录时，purchaser_id 必填
    
    result = await remote_session_manager.request(
        token, "POST", "/index.php", 
        params=params,
        data=data
    )
    
    if not result or result.get("code") != 0:
        return {"success": False, "message": "获取商品列表失败"}
    
    # 解析商品数据
    products = []
    for item in result.get("data", []):
        products.append({
            "id": str(item.get("goods_id", "")),
            "name": item.get("name", ""),
            "spec": item.get("spec", ""),
            "unit": item.get("unit", ""),
            "category": item.get("category_name", ""),
        })
    
    logger.info(f"[SyncProducts] Got {len(products)} products from remote API")
    
    # 重载知识库
    try:
        await knowledge_base.reload_from_remote(products)
        logger.info(f"[SyncProducts] Knowledge base reloaded with {len(products)} products")
    except Exception as e:
        logger.error(f"[SyncProducts] Reload error: {e}")
        return {"success": False, "message": f"向量化失败: {str(e)}"}
    
    return {
        "success": True, 
        "message": "商品库同步完成",
        "count": len(products)
    }


# ========== 订单接口（预留） ==========

@router.post("/order/submit")
async def submit_order(req: SubmitOrderRequest, authorization: Optional[str] = Header(None)):
    """
    提交订单
    """
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    logger.info(f"[SubmitOrder] Order submission request: {req.dict()}")
    
    # 1. 数据校验
    if not req.restaurantId:
        return {"success": False, "message": "请选择餐厅"}
    
    if not req.orderTypeId:
        return {"success": False, "message": "请选择订单类型"}
    
    if not req.items:
        return {"success": False, "message": "订单商品不能为空"}
    
    # 检查是否有未确认的商品 (goodsId 必须存在)
    for idx, item in enumerate(req.items):
        if not item.get("goodsId"):
            return {
                "success": False, 
                "message": f"第 {idx + 1} 行商品未确认，请先选择对应的订单商品"
            }
    
    # 2. 构造远端 API 请求数据
    payload = {
        "order_type": req.orderTypeId,
        "warehouse_id": req.restaurantId,
        "collect_date": req.date.replace("-", "/"), # 确保格式为 YYYY/MM/DD
        "remark": req.remark or "",
        "item": []
    }
    
    # 根据用户类型填充 supplier_id / purchaser_id
    if session.user_type == "purchaser":
        # 学校登录: supplier_id 为必填 (选中的配送商), purchaser_id 为自己
        payload["supplier_id"] = req.partnerId
        payload["purchaser_id"] = session.genus_id
    else:
        # 配送商登录: purchaser_id 为必填 (选中的学校), supplier_id 为自己
        payload["purchaser_id"] = req.partnerId
        payload["supplier_id"] = session.genus_id
        
    # 填充商品列表
    for item in req.items:
        payload["item"].append({
            "goods_id": str(item.get("goodsId")),
            "buy_quantity": str(item.get("quantity")),
            "buy_unit": str(item.get("unit")),
            "remark": str(item.get("remark") or "")
        })
        
    logger.info(f"[SubmitOrder] Sending payload to remote: {payload}")
    
    # 3. 发送请求
    result = await remote_session_manager.request(
        token, "POST", "/index.php",
        params={"op": "goods_order_set"},
        data=payload # request方法会自动处理json/data
    )
    
    logger.info(f"[SubmitOrder] Remote response: {result}")
    
    if result and result.get("code") == 0:
        return {
            "success": True,
            "message": "订单提交成功",
            "orderId": result.get("id"),
            "tradeNo": result.get("trade_no")
        }
    else:
        msg = result.get("msg") or result.get("message") or "提交失败"
        return {
            "success": False,
            "message": f"提交失败: {msg}"
        }

