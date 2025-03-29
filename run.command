#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 app.py &
sleep 2
open http://127.0.0.1:5000/check_mail
