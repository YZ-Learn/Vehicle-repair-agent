import sys, os
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import streamlit as st, time, uuid
from agent.repair_agent import RepairAgent
from storage.database import save_conversation, get_conversations, get_recent_sessions, save_feedback

st.set_page_config(page_title="车辆维修助手", page_icon="⚙", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>.main>div{padding-bottom:60px}.block-container{max-width:900px;padding-top:24px}h1{font-size:1.6rem!important;font-weight:600!important}.subtitle{color:#666;font-size:.85rem}.stChatMessage{max-width:85%}.history-block{border-left:2px solid #bbb;padding-left:10px;margin:6px 0}.history-time{color:#999;font-size:.75rem}.history-query{font-size:.85rem}</style>""", unsafe_allow_html=True)

def ensure_vector_db():
    from rag.vector_store import VectorStore
    from model.factory import ModelFactory
    vs = VectorStore(ModelFactory().create_embedding_model())
    if vs.count() == 0:
        from rag.ingest import ingest_all
        with st.spinner("首次启动，正在构建知识库索引..."):
            ingest_all(vs)

if "session_id" not in st.session_state:
    st.session_state.update(session_id=uuid.uuid4().hex[:12], messages=[], last_conv_id=None)
if "agent" not in st.session_state:
    with st.spinner("正在加载模型..."):
        ensure_vector_db()
        st.session_state.agent = RepairAgent()

with st.sidebar:
    st.markdown("<div style='font-size:1.2rem;font-weight:600'>车辆维修助手</div>", unsafe_allow_html=True)
    if st.button("新会话", use_container_width=True):
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.session_state.messages = []
        st.session_state.agent.reset_monitor()
        st.rerun()
    total = sum(m.get("tokens",0) for m in st.session_state.messages)
    st.caption(f"Token: ~{total}")

st.markdown("<h1>车辆维修助手</h1><div class='subtitle'>输入故障现象或故障码</div>", unsafe_allow_html=True)

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("你好，我是车辆维修助手。")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("描述故障或输入故障码..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("assistant"):
        with st.status("分析中...") as status:
            r = st.session_state.agent.chat(prompt)
            status.update(label="完成", state="complete")
        t = r["response"]
        st.markdown(t)
        save_conversation(st.session_state.session_id, prompt, t, r["tokens"], r["tools_called"], r["knowledge_used"])
    st.session_state.messages.append({"role":"assistant","content":t,"conv_id":0,"tokens":r["tokens"]})
    st.rerun()
