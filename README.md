# 📰 Customer News Monitor

Automatically monitors Estonian and international news for mentions of your key customers and sends Slack alerts.

## Features

- **Estonian media priority**: Scans ERR, Postimees, Delfi, Äripäev, Geenius RSS feeds
- **International coverage**: Uses NewsAPI.org for English news (optional)
- **Slack notifications**: Formatted alerts sent to your DM or channel
- **Zero maintenance**: Runs on a schedule, only alerts when news is found

---

## 🚀 Setup Guide

### Step 1: Create Slack Webhook

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name it "News Monitor" and select your workspace
4. Go to **"Incoming Webhooks"** → Turn ON
5. Click **"Add New Webhook to Workspace"**
6. Select the channel/DM where you want alerts (e.g., your own DM)
7. Copy the webhook URL (looks like `https://hooks.slack.com/services/T.../B.../xxx`)

### Step 2: Get NewsAPI Key (Optional - for international news)

1. Go to https://newsapi.org/register
2. Sign up for free (100 requests/day)
3. Copy your API key

### Step 3: Deploy to Google Cloud Functions

```bash
# Install Google Cloud CLI if not installed
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Deploy the function
cd customer_news_monitor

gcloud functions deploy customer-news-monitor \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point monitor_customer_news \
  --set-env-vars SLACK_WEBHOOK_URL="YOUR_WEBHOOK_URL" \
  --set-env-vars NEWS_API_KEY="YOUR_NEWSAPI_KEY" \
  --memory 256MB \
  --timeout 120s \
  --region europe-west1
```

### Step 4: Set Up Daily Schedule

```bash
# Create a Cloud Scheduler job to run daily at 8:00 AM Tallinn time
gcloud scheduler jobs create http customer-news-daily \
  --schedule="0 8 * * *" \
  --time-zone="Europe/Tallinn" \
  --uri="https://europe-west1-YOUR_PROJECT_ID.cloudfunctions.net/customer-news-monitor" \
  --http-method=GET \
  --location=europe-west1
```

---

## 🔧 Alternative Deployment Options

### Option A: Run Locally with Cron (Mac/Linux)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export NEWS_API_KEY="your-api-key"  # Optional

# Test run
python main.py

# Add to crontab for daily 8 AM runs
crontab -e
# Add: 0 8 * * * cd /path/to/customer_news_monitor && /usr/bin/python3 main.py
```

### Option B: Deploy to Vercel (Free tier)

1. Create `vercel.json`:
```json
{
  "functions": {
    "api/monitor.py": {
      "runtime": "python3.9"
    }
  },
  "crons": [{
    "path": "/api/monitor",
    "schedule": "0 8 * * *"
  }]
}
```

2. Move main.py to `api/monitor.py`
3. Deploy: `vercel deploy`

### Option C: GitHub Actions (Free)

Create `.github/workflows/news-monitor.yml`:

```yaml
name: Customer News Monitor

on:
  schedule:
    - cron: '0 6 * * *'  # 8 AM Tallinn = 6 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          NEWS_API_KEY: ${{ secrets.NEWS_API_KEY }}
```

---

## 📋 Monitored Companies

| Company | Search Terms | GP (12mo) |
|---------|--------------|-----------|
| Windak OÜ | Windak | €136,186 |
| Threod Systems AS | Threod Systems, Threod | €98,853 |
| Stora Enso Eesti AS | Stora Enso | €30,507 |
| Kabkin GmbH | Kabkin | €17,211 |
| Voka Masin AS | Voka Masin | €16,754 |
| LTH-Baas AS | LTH-Baas | €12,857 |
| CNC Grupp OÜ | CNC Grupp | €11,069 |
| ERICSSON EESTI AS | Ericsson Eesti | €10,969 |
| Lexa SLT OÜ | Lexa SLT | €5,904 |
| Shore Link OÜ | Shore Link | €5,451 |
| ECO POINT OÜ | ECO POINT | €4,430 |
| GoCraft OÜ | GoCraft | €4,237 |
| DIATEC | DIATEC | €3,662 |
| Nefab Packaging OÜ | Nefab | €3,351 |
| Skeleton Technologies | Skeleton Technologies | €2,630 |

### Updating the Customer List

Edit `CUSTOMERS` list in `main.py`. For each customer, specify:
- `name`: Display name for Slack notifications
- `search_terms`: List of terms to search for (use exact company name, common abbreviations)
- `company_id`: Fractory company ID (for reference)

---

## 📰 News Sources

### Estonian (Priority)
- ERR Business (err.ee/majandus)
- Postimees Business
- Delfi Business
- Äripäev
- Geenius (tech news)

### International (requires NewsAPI key)
- 80,000+ news sources
- English language
- Up to 1 month history (free tier)

---

## 🔍 Customization

### Add More Estonian Sources

Edit `ESTONIAN_RSS_FEEDS` in `main.py`:

```python
ESTONIAN_RSS_FEEDS = [
    # ... existing feeds ...
    {"name": "Your Source", "url": "https://example.com/rss"},
]
```

### Change Scan Frequency

- Cloud Scheduler: Edit the cron expression
- Local cron: Edit crontab
- GitHub Actions: Edit the schedule in workflow file

### Filter by Industry/Topic

Add keywords to the search in `search_estonian_rss()`:

```python
# Only alert if article mentions both company AND "manufacturing"
if term.lower() in content and "manufacturing" in content:
```

---

## 💡 Tips

1. **Test first**: Run `python main.py` locally before deploying
2. **Start broad**: Better to get false positives initially, then narrow down
3. **Check RSS validity**: Some feeds may change URLs over time
4. **Monitor costs**: NewsAPI free tier = 100 requests/day (enough for 15 companies × 2 terms)

---

## 📊 Cost Estimate

| Service | Free Tier | Expected Cost |
|---------|-----------|---------------|
| Google Cloud Functions | 2M invocations/mo | €0 |
| Cloud Scheduler | 3 jobs free | €0 |
| NewsAPI.org | 100 requests/day | €0 |
| **Total** | | **€0/month** |

---

## Need Help?

Ask Claude to help you:
- Add more customers to monitor
- Change the notification format
- Add filtering by topic/industry
- Integrate with other notification channels
