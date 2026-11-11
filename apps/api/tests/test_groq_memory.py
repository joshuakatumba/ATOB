"""FAKE – development only. Real database/auth; fake generation for repeatable memory checks."""

import pytest
from civis.providers import FakeProvider, GroqChunk, GroqProvider, Turn


def test_groq_chunk_and_env_configuration():
    chunk = GroqChunk.model_validate({"choices": [{"delta": {"content": "FAKE"}}]})
    assert chunk.choices[0].delta.content == "FAKE"


async def test_chat_memory_is_persisted_and_owner_scoped(chat_clients):
    app, client, stranger = chat_clients

    class RecordingProvider(FakeProvider):
        seen: list[list[Turn]] = []

        async def stream(self, system, messages):
            self.seen.append(messages)
            async for event in super().stream(system, messages):
                yield event

    app.state.model_provider = RecordingProvider.from_file()
    cid = (await client.post("/v1/conversations", json={"mode": "research"})).json()["id"]
    for message in ["FAKE remember marker BLUE", "FAKE recall the marker"]:
        result = await client.post(
            f"/v1/conversations/{cid}/messages", json={"content": message, "mode": "research"}
        )
        assert "event: done" in result.text
    seen = app.state.model_provider.seen[-1]
    assert seen[0].content == "FAKE remember marker BLUE"
    assert seen[-1].content == "FAKE recall the marker"
    assert any(turn.role == "assistant" for turn in seen)
    assert len((await client.get(f"/v1/conversations/{cid}")).json()["messages"]) == 4
    assert (await stranger.get(f"/v1/conversations/{cid}")).status_code == 404


@pytest.mark.skipif(
    not (
        __import__("os").getenv("GROQ_API_KEY")
        and __import__("os").getenv("CIVIS_RUN_LIVE_PROVIDER_TESTS") == "1"
    ),
    reason="Live provider checks require explicit opt-in",
)
async def test_live_groq_stream_and_memory():
    from civis.config import Settings

    settings = Settings.from_env().model_copy(update={"llm_max_output_tokens": 64})
    provider = GroqProvider(settings)
    events = [
        event
        async for event in provider.stream(
            "Return only the test marker requested by the user.",
            [
                Turn(role="user", content="FAKE test. My marker is BLUE-724."),
                Turn(role="assistant", content="BLUE-724"),
                Turn(role="user", content="What marker did I give? Return just the marker."),
            ],
        )
    ]
    assert "BLUE-724" in "".join(event.text for event in events)
    assert any(event.kind == "usage" for event in events)


async def test_owner_templates_import_and_render(chat_clients):
    import io
    import re
    import zipfile
    from html import unescape
    from pathlib import Path
    from xml.etree import ElementTree

    from civis.templates import (
        OwnerCatalog,
        import_owner_templates,
        render_html,
        render_parts,
        render_word,
    )

    app, client, _ = chat_clients
    settings = app.state.settings.model_copy(
        update={"owner_templates_file": "content/owner-supplied/templates.json"}
    )
    catalog = OwnerCatalog.model_validate_json(Path(settings.owner_templates_file).read_text())
    assert await import_owner_templates(app.state.engine, settings) == len(catalog.templates)
    assert await import_owner_templates(app.state.engine, settings) == len(catalog.templates)
    for item in catalog.templates:
        template = item.model_dump()
        values = {f.key: f"FAKE {f.key} <&>" for f in item.fields}
        parts = render_parts(template, values)
        preview = render_html(item.title, parts)
        with zipfile.ZipFile(io.BytesIO(render_word(item.title, parts))) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
            word_text = "".join(root.itertext())
        assert unescape(re.sub("<[^>]+>", "", preview)) == word_text
    detail = (await client.get("/v1/templates/lease-agreement")).json()
    assert detail["is_fake"] is False and detail["status"] == "approved"
