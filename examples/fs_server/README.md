# Filesystem Utilities FastAPI Service

Small FastAPI app exposing basic filesystem and process utilities.

Endpoints

- `GET /ls?path=...&show_hidden=...` — list directory entries or info for a file.
- `GET /stat?path=...` — get file/directory stat info.
- `GET /read?path=...&max_bytes=...` — read up to `max_bytes` from a file (text returned when UTF-8, otherwise base64).
- `GET /nproc` — number of CPUs.
- `GET /proc?limit=...` — list processes (uses `psutil` if available, otherwise parses `/proc`).

Security

By default the server restricts filesystem operations to the repository root. You can override by setting the `FS_BASE_DIR` environment variable to an absolute directory path.

Run

Install dependencies and run with `uvicorn`:

```bash
python -m pip install -r tools/fs_server/requirements.txt
uvicorn tools.fs_server.app:app --reload --host 127.0.0.1 --port 8000
```

Examples

List root of repository:

```bash
curl 'http://127.0.0.1:8000/ls?path=.'
```
