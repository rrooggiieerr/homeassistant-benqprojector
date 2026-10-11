"""A fake BenQ projector speaking the native LAN protocol (TCP port 8000, no prompt)."""

import asyncio


class FakeProjector:
    """Minimal emulation of a networked BenQ projector for tests."""

    def __init__(self, *, echo: bool = True, max_clients: int | None = None) -> None:
        self.echo = echo
        self.max_clients = max_clients
        self.power = "off"
        self.values = {
            "modelname": "LK935",
            "macaddr": "C0:C4:F9:18:A6:2F",
            "vol": "5",
            "mute": "off",
            "sour": "hdmi",
            "ltim": "61",
            "bri": "50",
            "appmod": "hdr",
            "asp": "16:9",
            "bc": "on",
        }
        # Commands answered with "Unsupported item" / "Block item".
        self.unsupported: set[str] = {"micvol", "ltim2", "3d"}
        self.blocked: set[str] = set()
        # Commands that are silently ignored (no answer at all).
        self.silent: set[str] = set()
        # Seconds to wait before answering, per command.
        self.delays: dict[str, float] = {}
        # Answer every connection attempt with a TCP reset.
        self.refuse = False
        self.received: list[str] = []
        self.connections = 0
        self._writers: set[asyncio.StreamWriter] = set()
        self._server: asyncio.base_events.Server | None = None
        self.port: int | None = None

    async def start(self, port: int = 0) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", port)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        self.reset_connections()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    def reset_connections(self) -> None:
        """Drop every client with a TCP reset, like the projector does."""
        for writer in list(self._writers):
            writer.transport.abort()
        self._writers.clear()

    @property
    def active_connections(self) -> int:
        return len(self._writers)

    def count(self, command: str) -> int:
        return sum(1 for received in self.received if received == command)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if self.refuse or (
            self.max_clients is not None and len(self._writers) >= self.max_clients
        ):
            writer.transport.abort()
            return

        self.connections += 1
        self._writers.add(writer)
        buffer = b""
        try:
            while True:
                data = await reader.read(100)
                if not data:
                    break
                buffer += data
                while b"\r" in buffer:
                    line, buffer = buffer.split(b"\r", 1)
                    line = line.strip()
                    if line:
                        await self._command(line.decode(), writer)
        except (ConnectionError, OSError):
            pass
        finally:
            self._writers.discard(writer)
            writer.close()

    async def _command(self, raw: str, writer: asyncio.StreamWriter) -> None:
        body = raw.strip("*#").lower()
        command, _, action = body.partition("=")
        self.received.append(command)

        if command in self.silent:
            return
        if delay := self.delays.get(command):
            await asyncio.sleep(delay)

        response = self._response(command, action)
        out = f"{raw}\r\n" if self.echo else ""
        out += f"{response}\r\n"
        writer.write(out.encode())
        await writer.drain()

    def _response(self, command: str, action: str) -> str:
        if command in self.unsupported:
            return "*Unsupported item#"
        if command in self.blocked:
            return "*Block item#"
        if command == "pow":
            if action in ("on", "off"):
                self.power = action
            return f"*POW={self.power.upper()}#"
        if self.power != "on" and command not in ("modelname", "macaddr", "ltim"):
            return "*Block item#"
        if command not in self.values:
            return "*Unsupported item#"
        if action == "?":
            return f"*{command.upper()}={self.values[command]}#"
        if action in ("+", "-"):
            self.values[command] = str(
                int(self.values[command]) + (1 if action == "+" else -1)
            )
            return f"*{command.upper()}={action}#"
        self.values[command] = action
        return f"*{command.upper()}={action.upper()}#"
