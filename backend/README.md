# Marketing AI Hub Backend

Backend Python 3.12.4 cho `marketing-ai-hub`, dung de:

- cung cap API cho dashboard/module frontend
- goi Ollama tu server thay vi goi truc tiep tu browser
- lam diem noi sau nay cho Facebook, LinkedIn, YouTube, TikTok, WordPress, GA4, GSC, Google Sheets

## Yeu cau

- Python `3.12.4`
- Ollama da cai tren may
- Model `qwen3:8b` da duoc pull neu muon generate content that

## Cai dat

```powershell
cd d:\MKTAI\marketing-ai-hub\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Chay development server

```powershell
cd d:\MKTAI\marketing-ai-hub\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Ollama

Chay Ollama truoc khi goi endpoint generate:

```powershell
ollama serve
ollama pull qwen3:8b
```

## Endpoint chinh

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/data-sync`
- `GET /api/analytics`
- `GET /api/content`
- `POST /api/content/generate`
- `GET /api/scheduler`
- `GET /api/campaigns`
- `GET /api/seo-insights`
- `GET /api/integrations`
- `GET /api/reports`
- `GET /api/settings/defaults`
- `GET /api/google/website/status`
- `POST /api/google/website/sync`

## Ghi chu

Du lieu dashboard/module van la mock data on dinh de frontend dung ngay.

Dong bo `Google Analytics 4 + Search Console -> Google Sheets` da co endpoint that, nhung de chay duoc ban can:

- `GOOGLE_ANALYTICS_PROPERTY_ID`
- `GOOGLE_SEARCH_CONSOLE_SITE_URL`
- `GOOGLE_SERVICE_ACCOUNT_JSON` hoac `GOOGLE_SERVICE_ACCOUNT_FILE`

Chi co `GOOGLE_API_KEY` va `GOOGLE_SERVICE_ACCOUNT_EMAIL` la chua du de doc du lieu private tu GA4/GSC va ghi vao Google Sheets.
