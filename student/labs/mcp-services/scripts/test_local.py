import asyncio
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from verify import verify

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    key = secrets.token_urlsafe(32)
    env = dict(os.environ, MCP_API_KEY=key, PYTHONNOUSERSITE="1")
    processes = []
    with tempfile.TemporaryDirectory(prefix="mcp-tests-") as directory:
        logs = []
        try:
            urls = []
            for service in ("partners", "complaints"):
                number = port()
                log = open(Path(directory) / f"{service}.log", "w+")
                logs.append(log)
                proc = subprocess.Popen([sys.executable, "-m", "uvicorn", f"services.{service}:app",
                                         "--host", "127.0.0.1", "--port", str(number), "--no-access-log"],
                                        cwd=ROOT, env=env, stdout=log, stderr=log)
                processes.append(proc)
                origin = f"http://127.0.0.1:{number}"
                deadline = time.monotonic() + 90
                while True:
                    if proc.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    try:
                        with urlopen(origin + "/healthz", timeout=2):
                            break
                    except (URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise TimeoutError(f"{service} startup timed out")
                        time.sleep(0.5)
                urls.append(origin + "/mcp")
            asyncio.run(verify(*urls, key))
            print("PASS: clean local processes and HTTP authorization")
        finally:
            for proc in processes:
                if os.name == "nt" and proc.poll() is None:
                    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                    f"$children = Get-CimInstance Win32_Process | Where-Object {{ $_.ParentProcessId -eq {proc.pid} }}; "
                                    "$children | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
                                    f"Stop-Process -Id {proc.pid} -Force -ErrorAction SilentlyContinue"],
                                   check=True, timeout=30)
                elif proc.poll() is None:
                    proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=15)
            for log in logs:
                log.close()


if __name__ == "__main__":
    main()
