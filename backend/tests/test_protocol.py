import pytest
from app.core.protocol import (
    EventType,
    WebSocketMessage,
    create_message,
    RowCompletePayload
)

def test_event_types():
    """测试事件类型枚举"""
    assert EventType.CONNECTION_ACK == "connection_ack"
    assert EventType.TASK_START == "task_start"
    assert EventType.ROW_COMPLETE == "row_complete"

def test_message_creation():
    """测试消息创建"""
    msg = create_message(
        EventType.TASK_START,
        "client_123",
        {"task_id": "task_1"}
    )
    
    assert msg["type"] == "task_start"
    assert msg["client_id"] == "client_123"
    assert msg["data"]["task_id"] == "task_1"
    assert "timestamp" in msg

def test_payload_validation():
    """测试 Payload 验证"""
    # 有效 Payload
    payload = RowCompletePayload(
        table_id="table_1",
        row={"col1": "val1"}
    )
    assert payload.table_id == "table_1"
    
    # 缺失字段
    with pytest.raises(ValueError):
        RowCompletePayload(table_id="table_1")  # 缺少 row

