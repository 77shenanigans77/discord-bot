This archive contains the multi-file Discord bot architecture only.

Keep your existing api_main.py unless you want to replace it manually.
If your existing Procfile.bot does not already run bot_main.py, set it to:
worker: python bot_main.py
