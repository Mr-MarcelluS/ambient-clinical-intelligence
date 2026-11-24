#!/usr/bin/env bash
set -eu
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
if [ ! -f .env ]; then cp .env.example .env; fi
printf 'Run: .venv/bin/python -m streamlit run app/main.py\n'
