import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(BASE_DIR, 'PRINT.apk')

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import backendlogic as app_module

app = app_module.app
