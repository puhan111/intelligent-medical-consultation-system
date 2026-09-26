import pytest

from scripts import prepare_rag_eval_fixtures as fixtures


DOCUMENTS = [
    {"source": "rag-eval://one", "source_type": "医学参考资料", "content": "[合成评测资料] one"},
    {"source": "rag-eval://two", "source_type": "医学参考资料", "content": "[合成评测资料] two"},
]


def setup_fixture_inputs(monkeypatch):
    monkeypatch.setattr(fixtures, "load_documents", lambda: DOCUMENTS)
    monkeypatch.setattr(fixtures.settings, "DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr(
        fixtures,
        "chunk_document",
        lambda content, source, source_type: [
            {"content": content, "metadata": {"source": source, "source_type": source_type}}
        ],
    )
    monkeypatch.setattr(fixtures, "segment", lambda content: content)


@pytest.mark.asyncio
async def test_embedding_failure_does_not_open_database(monkeypatch):
    setup_fixture_inputs(monkeypatch)
    calls = 0

    def embed(content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("embedding unavailable")
        return [0.0] * 1024

    monkeypatch.setattr(fixtures, "_embed", embed)
    monkeypatch.setattr(
        fixtures, "async_session", lambda: pytest.fail("database opened before embeddings completed")
    )

    with pytest.raises(RuntimeError, match="embedding unavailable"):
        await fixtures.main()


@pytest.mark.asyncio
async def test_placeholder_key_does_not_open_database(monkeypatch):
    setup_fixture_inputs(monkeypatch)
    monkeypatch.setattr(fixtures.settings, "DASHSCOPE_API_KEY", "dummy-api-key")
    monkeypatch.setattr(
        fixtures, "async_session", lambda: pytest.fail("database opened with placeholder key")
    )

    with pytest.raises(RuntimeError, match="Configure DASHSCOPE_API_KEY"):
        await fixtures.main()


@pytest.mark.asyncio
async def test_replaces_fixtures_in_one_transaction(monkeypatch, capsys):
    setup_fixture_inputs(monkeypatch)
    monkeypatch.setattr(fixtures, "_embed", lambda content: [0.0] * 1024)
    operations = []

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def begin(self):
            class Transaction:
                async def __aenter__(self):
                    operations.append("begin")

                async def __aexit__(self, exc_type, *args):
                    operations.append("commit" if exc_type is None else "rollback")

            return Transaction()

        async def execute(self, statement):
            assert operations == ["begin"]
            operations.append("delete")

        def add_all(self, chunks):
            assert operations == ["begin", "delete"]
            operations.append(("insert", len(chunks)))

    monkeypatch.setattr(fixtures, "async_session", Session)

    await fixtures.main()

    assert operations == ["begin", "delete", ("insert", 2), "commit"]
    assert '"failed_chunk_count": 0' in capsys.readouterr().out
