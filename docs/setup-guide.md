# Developer Setup Guide

This guide walks you through setting up the frontend, backend, and development environment for the NISAR platform.

## Prerequisites
- **Python:** 3.10 or higher
- **Node.js:** 18.0 or higher
- **npm:** 9.0 or higher
- **Git**

---

## 1. Automated Setup (Quickstart)

### On macOS / Linux:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### On Windows:
```cmd
scripts\setup.bat
```

---

## 2. Manual Step-by-Step Setup

### Step 2.1: Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate       # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment:
   ```bash
   cp .env.example .env
   ```
5. Run the development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - API Docs will be available at: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/health`

### Step 2.2: Frontend Setup
1. In a new terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Configure environment:
   ```bash
   cp .env.example .env
   ```
4. Start the Vite development server:
   ```bash
   npm run dev
   ```
   - Application UI will be live at: `http://localhost:3000`

---

## 3. Running Backend Tests
From the `backend` directory with the virtual environment activated:
```bash
pytest tests/
```
