"""数据库操作封装"""
from storage.models import db_session, Conversation, Feedback
from utils.logger_handler import logger


def save_conversation(
    session_id: str,
    user_query: str,
    agent_response: str,
    tokens_used: int = 0,
    tools_called: str = "",
    knowledge_used: str = "",
) -> int:
    """保存一条对话记录，返回记录ID"""
    conv = Conversation(
        session_id=session_id,
        user_query=user_query,
        agent_response=agent_response,
        tokens_used=tokens_used,
        tools_called=tools_called,
        knowledge_used=knowledge_used,
    )
    db_session.add(conv)
    db_session.commit()
    logger.debug(f"[DB] 保存对话记录 #{conv.id}")
    return conv.id


def get_conversations(session_id: str, limit: int = 50) -> list[dict]:
    """获取某个会话的历史记录"""
    rows = (
        db_session.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "user_query": r.user_query,
            "agent_response": r.agent_response,
            "tokens_used": r.tokens_used,
            "tools_called": r.tools_called,
            "knowledge_used": r.knowledge_used,
            "created_at": r.created_at.strftime("%H:%M:%S"),
        }
        for r in reversed(rows)
    ]


def get_recent_sessions(limit: int = 20) -> list[dict]:
    """获取最近的会话列表"""
    from sqlalchemy import func

    rows = (
        db_session.query(
            Conversation.session_id,
            Conversation.user_query,
            Conversation.created_at,
        )
        .order_by(Conversation.created_at.desc())
        .all()
    )

    seen = set()
    sessions = []
    for r in rows:
        if r.session_id not in seen:
            seen.add(r.session_id)
            sessions.append(
                {
                    "session_id": r.session_id,
                    "last_query": r.user_query[:40],
                    "last_time": r.created_at.strftime("%m-%d %H:%M"),
                }
            )
        if len(sessions) >= limit:
            break
    return sessions


def save_feedback(conversation_id: int, rating: int, comment: str = "") -> int:
    """保存用户反馈"""
    fb = Feedback(
        conversation_id=conversation_id,
        rating=rating,
        comment=comment,
    )
    db_session.add(fb)
    db_session.commit()
    logger.info(f"[DB] 反馈 #{conversation_id} → 评分 {rating}")
    return fb.id
