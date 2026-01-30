import os
import sys
import subprocess
import webbrowser
import time
import socket
from threading import Thread

def is_server_ready(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def start_django():
    # تشغيل سيرفر دجانغو بدون نافذة سوداء
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "8000", "--noreload"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        env=env
    )

if __name__ == "__main__":
    # 1. ابدأ السيرفر في خيط منفصل
    Thread(target=start_django, daemon=True).start()

    # 2. انتظر حتى يعمل السيرفر (بحد أقصى 10 ثوانٍ)
    url = "http://127.0.0.1:8000/pos/inventory/"
    for _ in range(10):
        if is_server_ready('127.0.0.1', 8000):
            webbrowser.open(url)
            break
        time.sleep(1)

    # 3. ابقِ البرنامج يعمل في الخلفية
    while True:
        time.sleep(100)