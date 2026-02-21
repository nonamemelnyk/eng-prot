# Chat Frontend

Standalone chat app (text + audio streaming).

## Run

```bash
cd frontend/web
npm start
```

Opens at **http://localhost:3000**

## Configuration

Backend must be running on port 8000. Change URL in `config.js`:

```js
window.CHAT_CONFIG = {
  wsUrl: "ws://localhost:8000/api/v1/ws/chat",
};
```

## Backend

```bash
cd /path/to/EngProt
python -m uvicorn backend.src.apps.prototype.main:app --host 0.0.0.0 --port 8000
```
