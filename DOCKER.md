# Docker

All Docker files are in the `docker/` folder.

## Run both services

```bash
cd docker
docker compose up --build
```

Or from project root:
```bash
docker compose -f docker/docker-compose.yml up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Requirements

Create `.env` in project root with:
```
GROQ_API_KEY=your_api_key
```

## Run separately

**Backend:**
```bash
docker build -f docker/backend.Dockerfile -t engprot-backend .
docker run -p 8000:8000 --env-file .env engprot-backend
```

**Frontend:**
```bash
docker build -f docker/frontend.Dockerfile -t engprot-frontend .
docker run -p 3000:80 engprot-frontend
```
