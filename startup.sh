#!/bin/bash
set -e

pip install -r requirements.txt --pre
PORT="${PORT:-8000}"
uvicorn app:app --host 0.0.0.0 --port "${PORT}"
