# 04. 后端工程开发文档 (Backend Engineering Spec)

## 1. 技术栈 (Tech Stack)
*   **Framework**: FastAPI (Python 3.10+)
*   **Agent Framework**: LangChain + LangGraph
*   **LLM Provider**: Aliyun DashScope SDK (Qwen-Max, Qwen-VL)
*   **Vector DB**: FAISS (内存版，通过 Pickle 持久化)
*   **Database**: MySQL (仅作为知识源同步)
*   **OCR/ASR**: Aliyun SDK

---

## 2. 目录结构 (Directory Structure)
```
backend/
├── app/
│   ├── api/
│   │   ├── endpoints.py         // RESTful 路由
│   │   └── websocket.py         // WS 处理
│   ├── core/
│   │   ├── config.py            // Env 加载
│   │   └── events.py            // Startup/Shutdown 钩子
│   ├── services/
│   │   ├── aliyun_ocr.py        // OCR 封装
│   │   ├── aliyun_asr.py        // ASR 封装
│   │   └── knowledge_sync.py    // MySQL -> FAISS 同步脚本
│   ├── agents/
│   │   ├── graph.py             // LangGraph 工作流定义
│   │   ├── master_agent.py      // 总控 Prompts
│   │   ├── visual_agent.py      // 视觉流逻辑
│   │   └── skills/
│   │       ├── database_skill.py // lookup_standard_entity 工具
│   │       └── form_skill.py     // 操作前端表格的 Tool 定义
│   └── models/
│       └── schemas.py           // Pydantic Models (与总控文档一致)
├── main.py
└── requirements.txt
```

---

## 3. 核心模块实现

### 3.1 数据库技能 (Database Skill)
文件: `app/agents/skills/database_skill.py`

*   **Function**: `lookup_standard_entity(query: str, category: str = None)`
*   **Implementation**:
    1.  加载 FAISS Index (在 app startup 时加载到内存)。
    2.  调用 `DashScope.Generation.call(model='text-embedding-v1', input=query)` 获取向量。
    3.  `index.search(vector, k=5)` 获取 Top-5 索引。
    4.  回查 Metadata 获取真实商品名。
    5.  计算文本相似度 (Levenshtein) 进行二次排序。
    6.  返回 List[str]。

### 3.2 LangGraph 工作流 (The Workflow)
文件: `app/agents/graph.py`

我们需要定义一个 **StateGraph**。

*   **State 定义**:
    ```python
    class AgentState(TypedDict):
        input_type: str
        messages: List[BaseMessage]
        current_image_url: Optional[str]
        form_data: Dict         # 当前表格数据
        ambiguity_flag: bool    # 是否有待确认项
    ```

*   **Nodes (节点)**:
    1.  `router_node`: 分析输入，决定去 `visual_flow` 还是 `audio_flow`。
    2.  `visual_node`: 调用 OCR -> 调用 V-LLM -> 调用 Database Skill -> 更新 `form_data`。
    3.  `audio_node`: 调用 ASR -> LLM 意图识别 -> 更新 `form_data` 或 生成 `messages` 回复。
    4.  `human_loop_node`: 如果 `ambiguity_flag` 为真，挂起并在 WebSocket 推送提问。

### 3.3 接口实现

#### POST `/api/workflow/visual`
```python
async def process_visual(file: UploadFile, template_id: str):
    # 1. Upload to OSS (Temporarily or local temp file)
    # 2. Trigger LangGraph with input
    result = await agent_graph.ainvoke({"input_type": "image", ...})
    return StandardResponse(data=result['form_data'])
```

#### WebSocket `/ws/agent`
```python
@router.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # 监听 LangGraph 的 stream_events
    async for event in agent_graph.astream_events(...):
        # 将内部思考过程转换为前端可读的 JSON
        await websocket.send_json({
            "type": "agent_thought",
            "content": event['content']
        })
```

---

## 4. 数据库同步逻辑
*   **Script**: `scripts/sync_db.py`
*   **Logic**:
    *   连接 MySQL。
    *   `SELECT name FROM products`.
    *   Batch Embedding (每批 50 条)。
    *   `faiss.IndexFlatL2`.
    *   `faiss.write_index(index, "vector_store.index")`.
*   **Trigger**:
    *   服务启动时自动加载。
    *   提供 API `/api/sync/knowledge` 手动触发更新。

