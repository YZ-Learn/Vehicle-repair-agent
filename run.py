"""
车辆维修智能助手 — 启动入口

用法：
  python run.py ingest      # 导入知识库到向量数据库（首次运行必须先执行）
  python run.py start       # 启动 Streamlit 前端
  python run.py status      # 查看知识库状态
"""

import sys
import os

# 国内下载 HuggingFace 模型用镜像（已设则跳过，云上部署默认直连）
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 把项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from rag.vector_store import VectorStore
from rag.ingest import ingest_all
from model.factory import ModelFactory
from utils.logger_handler import logger


def cmd_ingest():
    """导入知识库"""
    print("=" * 50)
    print("  🔧 知识库导入工具")
    print("=" * 50)

    factory = ModelFactory()
    embedding = factory.create_embedding_model()
    vs = VectorStore(embedding)

    print("\n📂 扫描知识库文件...")
    ingest_all(vs)

    count = vs.count()
    print(f"\n✅ 导入完成！向量库中共 {count} 个文档块")
    print(f"📁 存储位置：data/vector_db/")


def cmd_start():
    """启动 Streamlit 前端"""
    print("=" * 50)
    print("  🚀 启动车辆维修智能助手")
    print("=" * 50)
    print("\n正在启动 Streamlit...")
    print("打开浏览器访问：http://localhost:8501")
    print("\n按 Ctrl+C 停止服务\n")
    os.system(f"streamlit run {os.path.join(PROJECT_ROOT, 'app.py')}")


def cmd_status():
    """查看知识库状态"""
    factory = ModelFactory()
    embedding = factory.create_embedding_model()
    vs = VectorStore(embedding)
    count = vs.count()

    knowledge_dir = os.path.join(PROJECT_ROOT, "knowledge")
    file_count = len([f for f in os.listdir(knowledge_dir) if f.endswith(".md")]) if os.path.exists(knowledge_dir) else 0

    print(f"\n📊 知识库状态")
    print(f"  • 向量数据库位置：data/vector_db/")
    print(f"  • 文档块数量：{count}")
    print(f"  • 知识源：{file_count} 个 .md 文件")
    print(f"  • 模型配置：config/model.yml\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "ingest":
        cmd_ingest()
    elif command == "start":
        cmd_start()
    elif command == "status":
        cmd_status()
    else:
        print(f"未知命令: {command}")
        print(__doc__)
