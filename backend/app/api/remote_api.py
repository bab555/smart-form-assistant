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
    restaurantId: str
    orderTypeId: str
    date: str
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
    raw_data = result.get("data", [])
    
    for item in raw_data:
        if session.user_type == "purchaser":
            # 配送商列表
            partners.append({
                "id": str(item.get("supplier_id", "")),
                "name": item.get("supplier_name", ""),
            })
        else:
            # 学校列表
            partners.append({
                "id": str(item.get("purchaser_id", "")),
                "name": item.get("purchaser_name", ""),
            })
    
    logger.info(f"[Partners] parsed {len(partners)} items")
    return {"success": True, "data": partners}


@router.get("/data/restaurants")
async def get_restaurants(authorization: Optional[str] = Header(None)):
    """获取餐厅列表"""
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    result = await remote_session_manager.request(
        token, "POST", "/index.php", params={"op": "warehouse"}
    )
    
    if not result or result.get("code") != 0:
        return {"success": False, "data": [], "message": "获取失败"}
    
    restaurants = []
    for item in result.get("data", []):
        restaurants.append({
            "id": str(item.get("warehouse_id", "")),
            "name": item.get("warehouse_name", ""),
        })
    
    return {"success": True, "data": restaurants}


@router.get("/data/order_types")
async def get_order_types(authorization: Optional[str] = Header(None)):
    """获取订单类型列表"""
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    result = await remote_session_manager.request(
        token, "POST", "/index.php", params={"op": "order_type"}
    )
    
    if not result or result.get("code") != 0:
        return {"success": False, "data": [], "message": "获取失败"}
    
    order_types = []
    for item in result.get("data", []):
        order_types.append({
            "id": str(item.get("order_type_id", "")),
            "name": item.get("type_name", ""),
        })
    
    return {"success": True, "data": order_types}


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
    result = await remote_session_manager.request(
        token, "POST", "/index.php", 
        params={"op": "goods"},
        data={"supplier_id": req.partnerId}
    )
    
    if not result or result.get("code") != 0:
        return {"success": False, "message": "获取商品列表失败"}
    
    # 解析商品数据
    products = []
    for item in result.get("data", []):
        products.append({
            "id": str(item.get("goods_id", "")),
            "name": item.get("goods_name", ""),
            "spec": item.get("goods_spec", ""),
            "unit": item.get("goods_unit", ""),
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
    提交订单（预留接口）
    
    TODO: 待网站方提供接口文档后对接
    """
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = remote_session_manager.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="登录已过期")
    
    logger.info(f"[SubmitOrder] Order submission request: {req.dict()}")
    
    # 数据校验
    if not req.restaurantId:
        return {"success": False, "message": "请选择餐厅"}
    
    if not req.orderTypeId:
        return {"success": False, "message": "请选择订单类型"}
    
    if not req.items:
        return {"success": False, "message": "订单商品不能为空"}
    
    # 检查是否有未确认的商品
    for idx, item in enumerate(req.items):
        if not item.get("goodsId"):
            return {
                "success": False, 
                "message": f"第 {idx + 1} 行商品未确认，请先选择对应的订单商品"
            }
    
    # TODO: 实际提交到远端
    return {
        "success": False, 
        "message": "订单提交接口待对接，数据校验通过",
        "validatedItems": len(req.items)
    }

