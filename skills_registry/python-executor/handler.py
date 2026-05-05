"""Execute Python code in a sandboxed subprocess with timeout."""

import subprocess
import sys
import tempfile
import os


def handle(inputs: dict) -> dict:
    code = str(inputs.get("code", "")).strip()
    if not code:
        return {"error": "code is required"}

    timeout = max(1, min(int(inputs.get("timeout", 10)), 30))

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            # Isolate environment — no inherited secrets
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": "",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        return {
            "stdout": proc.stdout[:8000] if proc.stdout else "",
            "stderr": proc.stderr[:2000] if proc.stderr else "",
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "error": f"Execution timed out after {timeout}s",
            "stdout": "",
            "stderr": "",
            "returncode": -1,
        }
    except Exception as e:
        return {"error": f"Execution failed: {str(e)}"}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
