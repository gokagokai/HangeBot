@echo off

python -m venv venv
call venv/scripts/activate

pip install -r .\requirements.txt

echo Install complete.
pause