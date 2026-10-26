# sensu-telegram-handler

A [Sensu Go](https://sensu.io) pipe handler that sends events to a Telegram chat.

It is a single Python 3.12+ script that uses only the standard library, so the asset needs nothing on the backend except `python3`.

## Message

```
🆘 Check check-http on host web01 failing

HTTP CRITICAL: 502 Bad Gateway

Open in Sensu
```

| Status     | Icon |
| ---------- | ---- |
| 0 OK       | ✅   |
| 1 WARNING  | ⚠️   |
| 2 CRITICAL | 🆘   |
| 3+ UNKNOWN | ❔   |

- Check output is HTML-escaped and shown as preformatted text.
- Long output is cut so the message fits Telegram's 4096-character limit.
- Proxy entities (no `system.hostname`) are shown by entity name.
- The "Open in Sensu" link is added only when `--dashboard-url` is set.

## Configuration

| Setting                      | Required | Description                                                    |
| ---------------------------- | -------- | -------------------------------------------------------------- |
| `--chat-id`                  | yes      | Telegram chat ID to send to                                    |
| `--dashboard-url`            | no       | Sensu web UI URL, for example `https://sensu.example.com`      |
| `TELEGRAM_BOT_TOKEN` env var | yes      | Bot API token. Env only, so it never shows in the process list |

The handler exits with code 1 and prints the reason to stderr when the token is missing, the event is invalid, or Telegram rejects the message.
Sensu logs this in the backend journal.

## Usage

Asset (take the URL and sha512 from the release page):

```yaml
type: Asset
api_version: core/v2
metadata:
  name: sensu-telegram-handler
spec:
  builds:
    - url: https://github.com/mrGrab/sensu-telegram-handler/releases/download/v1.0.0/sensu-telegram-handler.tar.gz
      sha512: <from sensu-telegram-handler_sha512-checksums.txt>
      filters:
        - entity.system.os == 'linux'
```

Handler:

```yaml
type: Handler
api_version: core/v2
metadata:
  name: telegram
spec:
  type: pipe
  command: sensu-telegram-handler --chat-id 123456789 --dashboard-url https://sensu.example.com
  env_vars:
    - TELEGRAM_BOT_TOKEN=<bot token>
  runtime_assets:
    - sensu-telegram-handler
  filters:
    - is_incident
    - not_silenced
  timeout: 30
```

Manual test:

```sh
sensuctl event info <entity> <check> --format json \
  | TELEGRAM_BOT_TOKEN=<token> ./bin/sensu-telegram-handler --chat-id <id>
```

## Development

```sh
python3 -m unittest discover -s tests   # run tests
./build.sh                              # build dist/ (reproducible tarball + sha512)
```
