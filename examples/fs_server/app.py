from fastapi import FastAPI, HTTPException, Query
from pathlib import Path
from typing import List, Optional
import os
import base64

try:
    import psutil
except Exception:
    psutil = None

app = FastAPI(title="Filesystem Utilities API")

# Base directory allowed for operations. Defaults to the repository root (two levels up).
BASE_DIR = Path(os.getenv("FS_BASE_DIR") or Path(__file__).resolve().parents[2]).resolve()

def ensure_within_base(path: Path):
    path = path.resolve()
    try:
        path.relative_to(BASE_DIR)
    except Exception:
        raise HTTPException(status_code=403, detail="Path outside allowed base directory")

def file_info(p: Path):
    s = p.stat()
    return {
        "name": p.name,
        "path": str(p.relative_to(BASE_DIR)),
        "is_dir": p.is_dir(),
        "size": s.st_size,
        "mtime": s.st_mtime,
    }


@app.get("/ls")
def ls(path: str = ".", show_hidden: bool = Query(False)):
    p = (BASE_DIR / path).resolve()
    ensure_within_base(p)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if p.is_file():
        return file_info(p)
    entries = []
    for child in sorted(p.iterdir(), key=lambda x: x.name):
        if not show_hidden and child.name.startswith('.'):
            continue
        entries.append(file_info(child))
    return entries


@app.get("/stat")
def stat(path: str):
    p = (BASE_DIR / path).resolve()
    ensure_within_base(p)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    s = p.stat()
    return {
        "size": s.st_size,
        "mtime": s.st_mtime,
        "mode": s.st_mode,
        "uid": getattr(s, "st_uid", None),
        "gid": getattr(s, "st_gid", None),
        "is_dir": p.is_dir(),
    }


@app.get("/read")
def read(path: str, max_bytes: int = Query(10000, ge=1, le=10_000_000)):
    p = (BASE_DIR / path).resolve()
    ensure_within_base(p)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    b = p.open("rb").read(max_bytes + 1)
    truncated = len(b) > max_bytes
    if truncated:
        b = b[:max_bytes]
    try:
        text = b.decode("utf-8")
        return {"text": text, "truncated": truncated}
    except Exception:
        return {"base64": base64.b64encode(b).decode("ascii"), "truncated": truncated}


@app.get("/nproc")
def nproc():
    return {"nproc": os.cpu_count()}


@app.get("/proc")
def proc(limit: int = Query(50, ge=1, le=1000)):
    procs = []
    if psutil:
        for p in psutil.process_iter(attrs=["pid", "name", "username", "cmdline"]):
            info = p.info
            # cmdline might be list; make it a string for JSON
            if isinstance(info.get("cmdline"), list):
                info["cmdline"] = " ".join(info.get("cmdline") or [])
            procs.append(info)
            if len(procs) >= limit:
                break
    else:
        proc_dir = Path("/proc")
        for entry in sorted(proc_dir.iterdir(), key=lambda x: int(x.name) if x.name.isdigit() else -1):
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            cmd = ""
            try:
                cmd = entry.joinpath("cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
            except Exception:
                pass
            name = ""
            try:
                name = entry.joinpath("comm").read_text().strip()
            except Exception:
                pass
            procs.append({"pid": pid, "name": name, "cmdline": cmd})
            if len(procs) >= limit:
                break
    return {"processes": procs}
