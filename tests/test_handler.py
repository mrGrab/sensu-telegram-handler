from __future__ import annotations

import copy
import io
import json
import os
import sys
import unittest
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from typing import Any
from unittest import mock

# The handler has no .py extension, so load it explicitly
sys.dont_write_bytecode = True
HANDLER = str(Path(__file__).parent.parent / "bin" / "sensu-telegram-handler")
loader = SourceFileLoader("handler", HANDLER)
spec = spec_from_loader("handler", loader)
assert spec is not None
handler = module_from_spec(spec)
loader.exec_module(handler)

EVENT: dict[str, Any] = {
    "check": {
        "metadata": {"name": "check-http", "namespace": "default"},
        "status": 2,
        "state": "failing",
        "output": "HTTP CRITICAL: 502 <Bad Gateway> & more\n",
    },
    "entity": {
        "metadata": {"name": "web01"},
        "system": {"hostname": "web01.example.com"},
    },
}


def event(**check: object) -> dict[str, Any]:
    e = copy.deepcopy(EVENT)
    e["check"].update(check)
    return e


class BuildMessageTest(unittest.TestCase):
    def test_message(self) -> None:
        header = "🆘 <b>Check check-http on host web01.example.com failing</b>"
        output = "<pre>HTTP CRITICAL: 502 &lt;Bad Gateway&gt; &amp; more</pre>"
        self.assertEqual(handler.build_message(EVENT), f"{header}\n\n{output}")

    def test_status_icons(self) -> None:
        for status, icon in ((0, "✅"), (1, "⚠️"), (2, "🆘"), (3, "❔"), (127, "❔")):
            with self.subTest(status=status):
                self.assertTrue(
                    handler.build_message(event(status=status)).startswith(icon)
                )

    def test_escapes_names(self) -> None:
        e = event()
        e["check"]["metadata"]["name"] = "a<b>"
        self.assertIn("Check a&lt;b&gt; on", handler.build_message(e))

    def test_proxy_entity_uses_entity_name(self) -> None:
        e = event()
        del e["entity"]["system"]
        self.assertIn("on host web01 failing", handler.build_message(e))

    def test_empty_output_has_no_pre(self) -> None:
        self.assertNotIn("<pre>", handler.build_message(event(output="\n")))

    def test_dashboard_link(self) -> None:
        msg = handler.build_message(EVENT, "https://sensu.example.com/")
        url = "https://sensu.example.com/c/~/n/default/events/web01/check-http"
        self.assertTrue(msg.endswith(f'<a href="{url}">Open in Sensu</a>'))
        self.assertNotIn("<a href", handler.build_message(EVENT))

    def test_truncates_long_output(self) -> None:
        for output in ("x" * 10000, "&" * 10000):
            with self.subTest(char=output[0]):
                msg = handler.build_message(
                    event(output=output), "https://sensu.example.com"
                )
                self.assertLessEqual(len(msg), handler.MAX_LENGTH)
                self.assertIn(handler.TRUNCATED + "</pre>", msg)
                # an HTML entity is never cut in half
                self.assertNotRegex(msg, r"&(?!amp;)")


class MainTest(unittest.TestCase):
    def run_main(
        self, stdin: str, env: dict[str, str], send_error: Exception | None = None
    ) -> tuple[int, str, mock.MagicMock]:
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch("sys.stdin", io.StringIO(stdin)),
            mock.patch("sys.stderr", io.StringIO()) as stderr,
            mock.patch.object(handler, "send", side_effect=send_error) as send,
        ):
            code: int = handler.main(["--chat-id", "42"])
        return code, stderr.getvalue(), send

    def test_sends_message(self) -> None:
        code, _, send = self.run_main(json.dumps(EVENT), {"TELEGRAM_BOT_TOKEN": "t"})
        self.assertEqual(code, 0)
        send.assert_called_once_with("t", "42", handler.build_message(EVENT))

    def test_missing_token(self) -> None:
        code, err, send = self.run_main(json.dumps(EVENT), {})
        self.assertEqual(code, 1)
        self.assertIn("TELEGRAM_BOT_TOKEN", err)
        send.assert_not_called()

    def test_invalid_event(self) -> None:
        for stdin in ("not json", "{}"):
            with self.subTest(stdin=stdin):
                code, err, send = self.run_main(stdin, {"TELEGRAM_BOT_TOKEN": "t"})
                self.assertEqual(code, 1)
                self.assertIn("Invalid Sensu event", err)
                send.assert_not_called()

    def test_send_failure(self) -> None:
        error = RuntimeError("Telegram API error 400: Bad Request")
        env = {"TELEGRAM_BOT_TOKEN": "t"}
        code, err, _ = self.run_main(json.dumps(EVENT), env, error)
        self.assertEqual(code, 1)
        self.assertIn("Telegram API error 400", err)


if __name__ == "__main__":
    _ = unittest.main()
