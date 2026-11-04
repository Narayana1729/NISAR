@echo off
echo === Setting up NISAR Project ===

cd /d "%~dp0.."

if not exist "frontend\.env" (
    copy "frontend\.env.example" "frontend\.env"
    echo Created frontend\.env
)

if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env"
    echo Created backend\.env
)

echo Setting up Python virtual environment...
cd backend
if not exist "venv" (
    python -m venv venv
    echo Created virtual environment in backend\venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Backend dependencies installed.

echo Setting up Frontend dependencies...
cd ..\frontend
call npm install
echo Frontend dependencies installed.

echo === Setup Completed Successfully ===
pause
