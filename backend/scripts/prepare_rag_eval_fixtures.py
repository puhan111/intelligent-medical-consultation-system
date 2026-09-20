"""Replace the isolated synthetic RAG evaluation documents in PostgreSQL."""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import delete

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import async_session
from app.models.knowledge_chunk import KnowledgeChunk
from app.schedule.jobs.knowledge_embed import _embed_and_store


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

    async with async_session() as db:
        await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source.in_(sources)))
        await db.commit()

    succeeded = 0
    failed = 0
    for document in documents:
        current_succeeded, current_failed = await _embed_and_store(
            async_session,
            content=document["content"],
            source=document["source"],
            source_type=document["source_type"],
        )
        succeeded += current_succeeded
        failed += current_failed

    print(
        json.dumps(
            {
                "document_count": len(documents),
                "embedded_chunk_count": succeeded,
                "failed_chunk_count": failed,
            },
            ensure_ascii=False,
        )
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
