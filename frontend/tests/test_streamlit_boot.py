import subprocess
import sys
import time
import requests
from frontend.config import FRONTEND_DIR


def test_streamlit_boot_health():
    """
    Verify that Streamlit successfully starts up and serves HTTP traffic
    without crashing on import or initial page rendering.
    """
    port = 8505
    app_path = FRONTEND_DIR / "app.py"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        started = False
        for _ in range(25):
            try:
                res = requests.get(f"http://127.0.0.1:{port}/_stcore/health", timeout=1)
                if res.status_code == 200:
                    started = True
                    break
            except Exception:
                time.sleep(0.5)

        assert started, "Streamlit server failed to respond on health check"

        # Also probe root page
        root_res = requests.get(f"http://127.0.0.1:{port}/", timeout=2)
        assert root_res.status_code == 200
        assert "Streamlit" in root_res.text or "<!DOCTYPE html>" in root_res.text

    finally:
        proc.terminate()
        proc.wait(timeout=5)
