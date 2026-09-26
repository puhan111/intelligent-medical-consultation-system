"""Replace the isolated synthetic RAG evaluation documents in PostgreSQL."""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import delete, func

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import async_session
from app.models.knowledge_chunk import KnowledgeChunk
from app.core.config import settings
from app.services.common.chunking_service import chunk_document
from app.services.common.rag_service import _embed
from app.services.common.tokenizer import segment


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "rag_eval_documents.json"


def load_documents() -> list[dict]:
    documents = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for document in documents:
        if not document["source"].startswith("rag-eval://"):
            raise ValueError("evaluation sources must use the rag-eval:// namespace")
        if not document["content"].startswith("[合成评测资料"):
            raise ValueError("evaluation content must be marked as synthetic")
    return documents


async def main() -> None:
    documents = load_documents()
    sources = [document["source"] for document in documents]
    if settings.DASHSCOPE_API_KEY in {"", "dummy-api-key", "your_dashscope_api_key"}:
        raise RuntimeError("Configure DASHSCOPE_API_KEY before importing RAG fixtures")

    prepared = []
    for document in documents:
        pieces = chunk_document(
            document["content"], document["source"], document["source_type"]
        )
        if not pieces:
            raise ValueError(f"No chunks produced for {document['source']}")
        for piece in pieces:
            prepared.append(KnowledgeChunk(
                source=document["source"],
                content=piece["content"],
                embedding=_embed(piece["content"]),
                chunk_metadata=piece["metadata"],
                content_tsv=func.to_tsvector("simple", segment(piece["content"])),
            ))

    async with async_session() as db:
        async with db.begin():
            await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source.in_(sources)))
            db.add_all(prepared)

    print(
        json.dumps(
            {
                "document_count": len(documents),
                "embedded_chunk_count": len(prepared),
                "failed_chunk_count": 0,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
