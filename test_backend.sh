#!/bin/bash
cd /Users/raffael/Desktop/STAGE/TUG
source backend/.venv/bin/activate
uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload

