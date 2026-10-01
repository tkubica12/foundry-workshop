import os
import subprocess
import sys
import tempfile
from pathlib import Path

from protocol_check import main as check_protocol


def test_real_responses_protocol():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="lab07-host-") as temporary:
        environment = {**os.environ, "HOME": temporary, "USERPROFILE": temporary}
        for key in list(environment):
            if key.startswith("FOUNDRY_") or key.startswith("APPLICATIONINSIGHTS_"):
                environment.pop(key)
        with (Path(temporary) / "host.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, str(root / "tests" / "protocol_fixture.py")],
                cwd=root, env=environment, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                check_protocol()
            except Exception:
                log.flush()
                print((Path(temporary) / "host.log").read_text(encoding="utf-8"))
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
