"""知识库导入脚本 — 扫描 knowledge/ 目录，分块后写入 Chroma"""
import os
from utils.path_tool import get_abs_path
from utils.config_handler import load_config
from utils.logger_handler import logger


def load_knowledge_files(directory: str | None = None) -> list[dict]:
    """读取 knowledge/ 下的所有 .md 文件"""
    if directory is None:
        agent_cfg = load_config("agent.yml")
        directory = get_abs_path(agent_cfg.get("knowledge_dir", "knowledge"))

    files = []
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(directory, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        files.append({
            "source": fname.replace(".md", ""),
            "content": content.strip(),
        })
        logger.info(f"[Ingest] 发现: {fname}")
    return files


def chunk_document(content: str, source: str,
                   chunk_size: int = 500,
                   overlap: int = 80) -> list[tuple[str, dict]]:
    """将一篇文档拆成有重叠的块，保留标题结构"""
    lines = content.split("\n")
    chunks = []
    current_title = ""
    current_lines = []
    current_len = 0

    for line in lines:
        if line.startswith("##") or line.startswith("###"):
            if current_lines and current_len > 50:
                text = "\n".join(current_lines).strip()
                chunks.append((text, current_title))
            current_title = line.strip("# ")
            current_lines = [line]
            current_len = len(line)
            continue

        current_lines.append(line)
        current_len += len(line) + 1

        if current_len >= chunk_size:
            text = "\n".join(current_lines).strip()
            if text:
                chunks.append((text, current_title))
            overlap_chars = 0
            retain_lines = []
            for ol in reversed(current_lines):
                retain_lines.insert(0, ol)
                overlap_chars += len(ol) + 1
                if overlap_chars >= overlap:
                    break
            current_lines = retain_lines
            current_len = overlap_chars

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            chunks.append((text, current_title))

    result = []
    for i, (text, title) in enumerate(chunks):
        result.append((
            text,
            {
                "source": source,
                "title": title,
                "chunk_index": i,
            },
        ))
    return result


def ingest_all(vector_store, chunk_size: int | None = None, overlap: int | None = None):
    """入口：加载所有知识文档并入库"""
    cfg = load_config("chroma.yml")
    chunk_size = chunk_size or cfg.get("chunk_size", 500)
    overlap = overlap or cfg.get("chunk_overlap", 80)

    files = load_knowledge_files()
    if not files:
        logger.warning("[Ingest] knowledge/ 目录下没有 .md 文件")
        return

    all_docs = []
    all_metas = []
    for f in files:
        chunks = chunk_document(f["content"], f["source"], chunk_size, overlap)
        for text, meta in chunks:
            all_docs.append(text)
            all_metas.append(meta)

    logger.info(f"[Ingest] 总计 {len(all_docs)} 个文档块")
    if all_docs:
        vector_store.add_documents(all_docs, all_metas)
