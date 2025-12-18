import random
import asyncio

from junior.db import get_supabase_client, DocumentRepository
from junior.core.types import DocumentChunk


async def main() -> None:
    client = get_supabase_client()

    rows = client.document_chunks.select(
        "id,document_id,content,page_number,paragraph_number,metadata"
    ).limit(1).execute().data
    if not rows:
        raise SystemExit("No rows found in document_chunks")

    row = rows[0]

    vec = [random.random() for _ in range(384)]

    chunk = DocumentChunk(
        id=str(row["id"]),
        document_id=str(row["document_id"]),
        content=str(row["content"]),
        page_number=int(row["page_number"]),
        paragraph_number=row.get("paragraph_number"),
        metadata=row.get("metadata") or {},
        embedding=vec,
    )

    repo = DocumentRepository()
    await repo.save_chunk(chunk)

    updated = (
        client.document_chunks.select("id, embedding")
        .eq("id", chunk.id)
        .execute()
        .data[0]
    )
    emb = updated.get("embedding")
    print("embedding_is_null", emb is None)

    # RPC search using same vector should return at least this chunk
    res = (
        client.client.rpc(
            "match_document_chunks",
            {"query_embedding": vec, "match_threshold": 0.0, "match_count": 5},
        )
        .execute()
        .data
    )
    print("rpc_rows", len(res or []))
    if res:
        print("top_id", res[0].get("id"))


if __name__ == "__main__":
    asyncio.run(main())
