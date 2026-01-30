import os
import threading
import webview
from waitress import serve

# استيراد مكتبة شاشة الترحيب
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

def start_django():
    # استبدل pos باسم المجلد الذي يحتوي على settings.py و wsgi.py
    from myproject.wsgi import application 
    serve(application, host='127.0.0.1', port=8000)

if __name__ == '__main__':
    t = threading.Thread(target=start_django)
    t.daemon = True
    t.start()

    # إنشاء النافذة
    window = webview.create_window('Suit System - أحمد إبراهيم', 'http://127.0.0.1:8000')

    # إغلاق شاشة الترحيب فوراً عند بدء البرنامج
    if pyi_splash:
        pyi_splash.close()

    webview.start()