from typing import List, Dict, Any, Optional
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# 中文场景下字符数近似字数，chunk_size/chunk_overlap 为字符数
CHUNK_SIZE = 400
CHUNK_OVERLAP = 60

_HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def chunk_document(
    content: str,
    source: str,
    source_type: str
) -> List[Dict[str, Any]]:
    """
    结构感知切分知识文档：
    1. 按 Markdown 标题层级切分，保留标题路径
    2. 超长段落用 RecursiveCharacterTextSplitter 二次切分（chunk_size=400, overlap=60）

    Args:
        content: 文档全文（Markdown 格式）
        source: 原文档标题/路径
        source_type: 分诊指引 / 医学参考资料

    Returns:
        每个元素包含 content 和 metadata（source, source_type, section_title）
    """
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=_HEADERS_TO_SPLIT_ON)
    header_docs = header_splitter.split_text(content)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks: List[Dict[str, Any]] = []
    for doc in header_docs:
        section_title = " / ".join(
            doc.metadata.get(level) for level in ("h1", "h2", "h3") if doc.metadata.get(level)
        )

        for piece in char_splitter.split_text(doc.page_content):
            if not piece.strip():
                continue
            chunks.append({
                "content": piece,
                "metadata": {
                    "source": source,
                    "source_type": source_type,
                    "section_title": section_title or None,
                }
            })

    return chunks
