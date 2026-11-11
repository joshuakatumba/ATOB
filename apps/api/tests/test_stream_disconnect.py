"""FAKE – development only: proxy streaming, heartbeats and upstream cancellation."""

import asyncio
import socket
import subprocess
from uuid import uuid4

import httpx
import pytest
import uvicorn
from civis.providers import FakeProvider


@pytest.mark.parametrize(
    "delay,target,balance", [(0.1, "event: delta", 19), (16, ": heartbeat", 20)]
)
async def test_proxy_disconnect_cancels_upstream_and_persists(
    chat_clients,
    tmp_path,
    delay,
    target,
    balance,
):
    app, first, _ = chat_clients
    provider = FakeProvider.from_file(delay=delay)
    app.state.model_provider = provider
    conversation = (await first.post("/v1/conversations", json={"mode": "research"})).json()["id"]
    path = "/v1/conversations/" + conversation
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    backend_port = sock.getsockname()[1]
    sock.listen(128)
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    proxy_port = probe.getsockname()[1]
    probe.close()
    config = tmp_path / "nginx.conf"
    config.write_text(
        "events {}\nhttp { access_log off; error_log /dev/null crit; server { "
        f"listen {proxy_port}; location / {{ proxy_pass http://127.0.0.1:{backend_port}; "
        "proxy_buffering off; proxy_read_timeout 360s; } } }"
    )
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", access_log=False, log_config=None))
    running = asyncio.create_task(server.serve(sockets=[sock]))
    name = "civis-test-proxy-" + uuid4().hex
    try:
        async with asyncio.timeout(10):
            while not server.started:
                await asyncio.sleep(0.02)
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--network",
                "host",
                "--name",
                name,
                "-v",
                str(config) + ":/etc/nginx/nginx.conf:ro",
                "nginx:1.28.0",
            ],
            check=True,
            capture_output=True,
        )
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{proxy_port}", headers=dict(first.headers), timeout=30
        ) as client:
            async with asyncio.timeout(10):
                while True:
                    try:
                        if (await client.get("/v1/health")).status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    await asyncio.sleep(0.05)
            async with client.stream(
                "POST",
                path + "/messages",
                json={
                    "content": "FAKE – development only",
                    "mode": "research",
                },
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith(target):
                        break
                else:
                    pytest.fail("Expected streaming event did not arrive through the proxy")
        await asyncio.wait_for(provider.cancelled.wait(), timeout=5)
        async with asyncio.timeout(5):
            while True:
                messages = (await first.get(path)).json()["messages"]
                remaining = (await first.get("/v1/me")).json()["prompts_left"]
                if messages[1]["status"] == "incomplete" and remaining == balance:
                    break
                await asyncio.sleep(0.05)
        assert bool(messages[1]["content"]) is (target == "event: delta")
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
        server.should_exit = True
        await asyncio.wait_for(running, timeout=10)
