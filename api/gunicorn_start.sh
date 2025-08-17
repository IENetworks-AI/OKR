#!/usr/bin/env bash
set -e
cd /home/ubuntu/ai-project-template
source venv/bin/activate
exec gunicorn -b 127.0.0.1:5000 -w 2 api.app:app
