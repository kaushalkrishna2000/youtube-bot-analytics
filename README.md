# YouTube Bot Analytics (Lambda Batch Only)

This branch is a Lambda-only implementation for channel batch analytics.

Legacy CLI and video-mode workflows were intentionally removed in this branch.

## Branch Scope (Intentional Removals)

The following surfaces were removed on purpose in branch `lambda/youtube-bot-analytics-fetch`:
- `src/main.py`
- `src/api/`
- `src/cli/`
- `src/export/`
- `src/credentials/`

This branch supports only Lambda batch fetch flow.

## What This Implementation Supports

- Lambda runtime entrypoint: `lambda_function.lambda_handler`
- Programmatic runner: `run_fetch_job(...)`
- Channel inputs from:
  - `DEFAULT_CHANNELS` in `src/lambda_function.py` (if non-empty)
  - otherwise `YOUTUBE_CHANNELS` env var (comma-separated)
- In-memory JSON result payload from runner
- API Gateway-style Lambda response envelope from handler

## Runtime Contract

### 1) Lambda Entrypoint

File: `src/lambda_function.py`

Handler:

```python
from lambda_function import lambda_handler
```

Deployment handler name:

```text
lambda_function.lambda_handler
```

Notes:
- Function signature stays `lambda_handler(event, context)` for AWS compatibility.
- `event` and `context` are intentionally unused in this version.

### 2) Channel Resolution Precedence

Inside `lambda_handler`:
1. Use `DEFAULT_CHANNELS` when non-empty.
2. Else parse `YOUTUBE_CHANNELS` as comma-separated values.

If no valid channels are resolved, handler returns `400`.

### 3) Runner API

Callable:

```python
from lambda_runner import run_fetch_job

result = run_fetch_job(
    channels=["@HombaleFilms", "https://www.youtube.com/@MrBeast"],
    include_comments=True,
    max_videos=10,
    max_comments=1000,
    delay_ms=None,
    quiet=True,
)
```

Returned payload schema:
- `ok` (bool)
- `error` (string or null)
- `summary` (`total`, `success`, `failed`)
- `reports` (list)
- `failures` (list of `{channel_input, error}`)
- `config_used` (resolved runtime config)

## Required Environment Variables

- `YOUTUBE_API_KEY` (required)
- `YOUTUBE_CHANNELS` (required when `DEFAULT_CHANNELS` is empty)

Example:

```bash
export YOUTUBE_API_KEY="your_api_key_here"
export YOUTUBE_CHANNELS="@HombaleFilms,@MrBeast,UCX6OQ3DkcsbYNE6H8uQQuVA"
```

Optional:
- `YOUTUBE_REQUEST_DELAY_MS`

## Lambda Layer Setup (protoenv)

Build dependency layer zip:

```bash
mkdir -p python
conda run -n protoenv pip install -r requirements.txt -t python/
zip -r layer.zip python
```

Deploy notes:
- Publish `layer.zip` as a Lambda layer and attach it to your function.
- Package app source separately (include `src/` in function artifact).
- Keep secrets/config in Lambda environment variables.

## Response Envelope

`lambda_handler` returns:
- `statusCode`
- `headers`
- `body` (JSON string)

Error case example (no channels configured):

```json
{
  "statusCode": 400,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"ok\":false,\"error\":\"No channels configured...\"}"
}
```

## Next Step (Part 2)

Mongo ingest is intentionally deferred to a separate implementation:
- Fetch Lambda writes immutable JSON outputs to S3.
- A separate S3-triggered Lambda ingests those JSON files into MongoDB with append-safe, idempotent upserts.
