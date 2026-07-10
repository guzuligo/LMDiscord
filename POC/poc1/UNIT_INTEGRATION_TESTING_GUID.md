# Unit & Integration Testing Guide

> AI Agent reference: Read this before running any tests.

## ⚠️ Critical: Always Use venv
- **Never use global `python`** — always activate venv first:
  ```bash
  source venv/bin/activate
  python -m pytest ...
  ```
- If no venv exists: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

## ⚠️ Always Check .env File
- `.env` contains all Discord tokens (bot token, guild ID, channel IDs)
- Tests that interact with Discord **require** `.env` to exist and be valid
- Path: `LMDiscord/POC/poc1/.env` (relative to project root)

## Test Locations
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Existing `test_*` files are placeholders — may be recreated/disposed

## LMStudio Endpoint
- Runs on `localhost:1234` — hard-coded in tests and config

## Quick Commands
```bash
source venv/bin/activate          # activate first!
pytest tests/unit/ -v             # unit tests
pytest tests/integration/ -v      # integration tests
pytest -m "not integration" -v    # fast unit-only run
```

## Test File Naming
- Unit: `tests/unit/test_<module_name>.py`
- Integration: `tests/integration/test_integration_<feature>.py`