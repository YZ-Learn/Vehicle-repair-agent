"""数据模型：对话历史、用户反馈"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from utils.path_tool import get_abs_path
import os

Base = declarative_base()


class Conversation(Base):
    """单次对话记录"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=False, comment="会话ID")
    user_query = Column(Text, nullable=False, comment="用户问题")
    agent_response = Column(Text, nullable=False, comment="Agent回复")
    tokens_used = Column(Integer, default=0, comment="本次消耗Token数")
    tools_called = Column(String(256), default="", comment="调用的工具列表")
    knowledge_used = Column(String(256), default="", comment="参考的知识文档")
    created_at = Column(DateTime, default=datetime.now, comment="时间")


class Feedback(Base):
    """用户反馈"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=False, comment="关联对话ID")
    rating = Column(Integer, default=0, comment="评分 1-5")
    comment = Column(Text, default="", comment="评论文本")
    created_at = Column(DateTime, default=datetime.now)


def init_db():
    """初始化 SQLite 数据库"""
    db_dir = get_abs_path("data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "chat_history.db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# 全局 session
db_session = init_db()
