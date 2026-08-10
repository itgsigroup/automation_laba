@echo off
cd /d "%~dp0"
python gsi_report.py >> run_log.txt 2>&1
