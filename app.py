"""
车辆维修智能助手 — Streamlit 前端

启动方式：
  cd E:\AI\Agent通用
  streamlit run app.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 国内下载 HuggingFace 模型用镜像（云上部署默认直连）
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import streamlit as st
import time
import uuid
from agent.repair_agent import RepairAgent
from storage.database import (
    save_conversation,
    get_conversations,
    get_recent_sessions,
    save_feedback,
)
from utils.logger_handler import logger

# ─── 页面配置 ─────────────────────────────

st.set_page_config(
    page_title="车辆维修助手",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 样式 ─────────────────────────────────

st.markdown("""
<style>
    .main > div { padding-bottom: 60px; }
    .block-container { max-width: 900px; padding-top: 24px; }
    h1 { font-size: 1.6rem !important; font-weight: 600 !important; margin-bottom: 4px !important; }
    .subtitle { color: #666; font-size: 0.85rem; margin-bottom: 20px; }
    .stChatMessage { max-width: 85%; }
    .sidebar-item { font-size: 0.85rem; padding: 4px 0; }
    .history-block { border-left: 2px solid #bbb; padding-left: 10px; margin: 6px 0; }
    .history-time { color: #999; font-size: 0.75rem; }
    .history-query { font-size: 0.85rem; margin: 2px 0; }
    .metric-card { text-align: center; padding: 6px; }
    .metric-label { font-size: 0.75rem; color: #888; }
    .metric-value { font-size: 1.1rem; font-weight: 500; }
</style>
""", unsafe_allow_html=True)


# ─── 首次启动：自动导入知识库 ──────────────

def ensure_vector_db():
    """检查向量库是否存在，不存在则自动导入"""
    from rag.vector_store import VectorStore
    from model.factory import ModelFactory

    factory = ModelFactory()
    embedding = factory.create_embedding_model()
    vs = VectorStore(embedding)

    if vs.count() == 0:
        logger.info("[Startup] 向量库为空，自动导入知识库...")
        from rag.ingest import ingest_all
        with st.spinner("首次启动，正在构建知识库索引，请稍候..."):
            ingest_all(vs)
        logger.info(f"[Startup] 导入完成，共 {vs.count()} 个文档块")


# ─── Session 状态 ──────────────────────────

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:12]
if "agent" not in st.session_state:
    with st.spinner("正在加载模型，请稍候..."):
        ensure_vector_db()
        st.session_state.agent = RepairAgent()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_conv_id" not in st.session_state:
    st.session_state.last_conv_id = None


# ─── 侧边栏 ──────────────────────────────

with st.sidebar:
    st.markdown("<div style='font-size:1.2rem; font-weight:600; margin-bottom:12px;'>车辆维修助手</div>", unsafe_allow_html=True)

    st.caption(f"会话 | {st.session_state.session_id[:8]}...")

    if st.button("新会话", use_container_width=True, type="secondary"):
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.session_state.messages = []
        st.session_state.last_conv_id = None
        st.session_state.agent.reset_monitor()
        st.rerun()

    st.divider()

    st.markdown("<div style='font-size:0.9rem; font-weight:500; margin-bottom:8px;'>最近会话</div>", unsafe_allow_html=True)
    recent = get_recent_sessions(8)
    for s in recent:
        if st.button(
            s['last_query'],
            key=f"sid_{s['session_id']}",
            use_container_width=True,
            help=f"{s['last_time']}",
        ):
            st.session_state.session_id = s["session_id"]
            st.rerun()

    st.divider()

    with st.expander("使用说明"):
        st.markdown("""
        **输入示例：**
        - 发动机故障灯亮，报 P0300
        - 刹车异响怎么查
        - 空调不制冷了
        - 换刹车片要多久
        - 拆燃油泵注意事项
        """)

    if st.session_state.messages:
        total_tokens = sum(
            m.get("tokens", 0) for m in st.session_state.messages if "tokens" in m
        )
        st.caption(f"会话消耗 ~{total_tokens} Token")

    st.divider()
    st.caption("v1.0")


# ─── 主界面 ──────────────────────────────

st.markdown("<h1>车辆维修智能助手</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>输入车辆故障现象或故障码，获取诊断建议和维修方案</div>", unsafe_allow_html=True)

# 欢迎消息
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("你好，我是车辆维修助手。描述故障现象或直接输入故障码即可。")

# 消息渲染
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("conv_id"):
            col1, col2 = st.columns([1, 10])
            with col1:
                if st.button("+1", key=f"up_{msg['conv_id']}", help="有帮助"):
                    save_feedback(msg["conv_id"], 5)
                    st.toast("已记录")
            with col2:
                if st.button("-1", key=f"down_{msg['conv_id']}", help="没帮助"):
                    save_feedback(msg["conv_id"], 1)
                    st.toast("已记录")

# 输入框
if prompt := st.chat_input("描述故障或输入故障码..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.status("分析中...", expanded=True) as status:
            result = st.session_state.agent.chat(prompt)
            response_text = result["response"]
            knowledge_used = result["knowledge_used"]
            tools_called = result["tools_called"]
            tokens_used = result["tokens_used"]

            info_items = []
            if tools_called:
                info_items.append(f"工具: {tools_called}")
            if knowledge_used != "无":
                info_items.append("知识库: 已检索")
            info_items.append(f"Token: {tokens_used}")
            st.markdown(f"<div style='font-size:0.75rem; color:#888; margin-bottom:8px;'>{' | '.join(info_items)}</div>",
                        unsafe_allow_html=True)

            status.update(label="回答完成", state="complete")

        # 流式输出
        response_placeholder = st.empty()
        displayed = ""
        for char in response_text:
            displayed += char
            response_placeholder.markdown(displayed + "▌")
            time.sleep(0.008)
        response_placeholder.markdown(displayed)

        conv_id = save_conversation(
            session_id=st.session_state.session_id,
            user_query=prompt,
            agent_response=response_text,
            tokens_used=tokens_used,
            tools_called=tools_called,
            knowledge_used=knowledge_used,
        )

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "conv_id": conv_id,
        "tokens": tokens_used,
    })

    st.rerun()


# ─── 历史记录 ──────────────────────────

conversations = get_conversations(st.session_state.session_id, limit=20)
if conversations:
    with st.expander("当前会话记录"):
        for c in conversations:
            st.markdown(f"""
            <div class='history-block'>
                <div class='history-time'>{c['created_at']}</div>
                <div class='history-query'><b>Q:</b> {c['user_query'][:60]}</div>
                <div class='history-query'><b>A:</b> {c['agent_response'][:80]}...</div>
            </div>
            """, unsafe_allow_html=True)
