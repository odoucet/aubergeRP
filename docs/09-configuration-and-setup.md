# Configuration

## config.yaml

Copy `config.example.yaml` to `config.yaml`. Settings can also be changed from the Admin UI.

```yaml
app:
  host: "0.0.0.0"
  port: 8123
  log_level: "INFO"      # DEBUG | INFO | WARNING | ERROR
  data_dir: "data"

active_connectors:
  text: ""               # set by Admin UI
  image: ""

user:
  name: "User"           # {{user}} macro replacement

scheduler:
  enabled: false
  interval_seconds: 86400
  cleanup_older_than_days: 30

chat:
  context_window: 4096
  summarization_threshold: 0.75
  ooc_protection: true

gui:
  custom_css: ""
  custom_header_html: ""
  custom_footer_html: ""

marketplace:
  index_url: "https://raw.githubusercontent.com/odoucet/aubergeRP/main/marketplace/index.json"
```

## Environment variable overrides

| Variable | Config key |
|---|---|
| `AUBERGE_DATA_DIR` | `app.data_dir` |
| `AUBERGE_HOST` | `app.host` |
| `AUBERGE_PORT` | `app.port` |
| `AUBERGE_LOG_LEVEL` | `app.log_level` |
| `AUBERGE_USER_NAME` | `user.name` |
| `AUBERGE_SENTRY_DSN` | `app.sentry_dsn` |
| `AUBERGE_ADMIN_PASSWORD_HASH` | `app.admin_password_hash` |
| `AUBERGE_LLM_API_URL` + `AUBERGE_LLM_MODEL` | Auto-provision text connector on startup |
| `AUBERGE_IMG_API_URL` + `AUBERGE_IMG_MODEL` | Auto-provision image connector on startup |

## Admin password

Generated on first startup and printed to the console. To reuse across restarts, copy the hash into `config.yaml:app.admin_password_hash` or set `AUBERGE_ADMIN_PASSWORD_HASH`.
