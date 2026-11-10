import os

bind = "0.0.0.0:5000"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
worker_class = "sync"
timeout = 60
graceful_timeout = 30
preload_app = False
errorlog = "-"
accesslog = None  # The application emits structured JSON request logs.
