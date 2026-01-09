# 🔧 Troubleshooting Guide

## ❌ Backend Not Starting / Docs Not Working

### Step 1: Check Dependencies

```bash
cd agentic-rag-assistant/backend
source venv/bin/activate
pip install fastapi uvicorn langchain langchain-openai langchain-pinecone langchain-community langgraph pinecone-client pypdf python-dotenv pydantic pydantic-settings -q
```

### Step 2: Verify .env File

Make sure `backend/.env` exists and has your API keys:

```bash
cd backend
cat .env | grep -E "OPENAI_API_KEY|PINECONE_API_KEY" | head -2
```

Should show your keys (don't share them!).

### Step 3: Start Backend Manually

**Option A: Using the script**
```bash
cd backend
./start_server.sh
```

**Option B: Direct command**
```bash
cd backend
source venv/bin/activate
python main.py
```

### Step 4: Check for Errors

Look for error messages in the terminal. Common issues:

1. **"API key not found"**
   - Check `.env` file exists
   - Verify keys are correct

2. **"Module not found"**
   - Run: `pip install -r ../requirements.txt`

3. **"Port already in use"**
   - Kill process: `lsof -ti:8000 | xargs kill`
   - Or change port in `.env`

4. **"Pinecone connection failed"**
   - Check Pinecone API key
   - Verify internet connection

### Step 5: Test Backend

Once running, test:

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","timestamp":"...","agent_loaded":true,"version":"1.0.0"}
```

## ✅ Quick Fix Commands

```bash
# Install all dependencies
cd backend
source venv/bin/activate
pip install fastapi uvicorn langchain langchain-openai langchain-pinecone langchain-community langgraph pinecone-client pypdf python-dotenv pydantic pydantic-settings langchain-text-splitters

# Start server
python main.py
```

## 🎯 Expected Output

When backend starts successfully, you should see:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     ✅ Agent graph loaded successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## 📍 Access Points

Once running:
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Chat**: http://localhost:8000/chat

---

**If still having issues, share the error message from the terminal!** 🔧
