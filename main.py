"""
Customer News Monitor - Cloud Function
Monitors news for mentions of your key customers and sends Slack alerts.

Deploy to: Google Cloud Functions, AWS Lambda, or run as a cron job
Schedule: Recommended daily at 8:00 AM local time

Required environment variables:
- NEWS_API_KEY: Your NewsAPI.org API key (free tier: 100 requests/day)
- SLACK_WEBHOOK_URL: Your Slack incoming webhook URL
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional
import feedparser  # For Estonian RSS feeds
import re

# ============================================================================
# CONFIGURATION - All customers in Kait's portfolio (47 companies)
# ============================================================================

CUSTOMERS = [
    # Top tier (>€20K GP)
    {"name": "Windak OÜ", "search_terms": ["Windak"], "company_id": 4622},
    {"name": "Threod Systems AS", "search_terms": ["Threod Systems", "Threod"], "company_id": 3214},
    {"name": "Stora Enso Eesti AS", "search_terms": ["Stora Enso"], "company_id": 847},
    {"name": "Kabkin GmbH & Co.KG", "search_terms": ["Kabkin"], "company_id": 5791},
    {"name": "Voka Masin AS", "search_terms": ["Voka Masin"], "company_id": 372},
    {"name": "LTH-Baas AS", "search_terms": ["LTH-Baas", "LTH Baas"], "company_id": 931},
    
    # Mid tier (€5K-€20K GP)
    {"name": "Äike Mobility OÜ", "search_terms": ["Äike", "Aike Mobility"], "company_id": 7064},
    {"name": "CNC Grupp OÜ", "search_terms": ["CNC Grupp"], "company_id": 338},
    {"name": "ERICSSON EESTI AS", "search_terms": ["Ericsson Eesti", "Ericsson Estonia"], "company_id": 11261},
    {"name": "B&W Metall OÜ", "search_terms": ["B&W Metall", "BW Metall"], "company_id": 944},
    {"name": "Lexa SLT OÜ", "search_terms": ["Lexa SLT"], "company_id": 9136},
    {"name": "Borg OÜ", "search_terms": ["Borg OÜ"], "company_id": 349},
    {"name": "Shore Link OÜ", "search_terms": ["Shore Link"], "company_id": 6562},
    {"name": "GoCraft OÜ", "search_terms": ["GoCraft"], "company_id": 3816},
    
    # Lower-mid tier (€1K-€5K GP)
    {"name": "Nefab Packaging OÜ", "search_terms": ["Nefab Packaging", "Nefab"], "company_id": 9692},
    {"name": "ECO POINT OÜ", "search_terms": ["ECO POINT", "Eco Point"], "company_id": 582},
    {"name": "Skeleton Technologies GmbH", "search_terms": ["Skeleton Technologies"], "company_id": 4693},
    {"name": "DIATEC", "search_terms": ["DIATEC"], "company_id": 12335},
    {"name": "Rapla Metall OÜ", "search_terms": ["Rapla Metall"], "company_id": 432},
    {"name": "AQ Lasertool OÜ", "search_terms": ["AQ Lasertool"], "company_id": 7989},
    {"name": "Elelevi OÜ", "search_terms": ["Elelevi"], "company_id": 9669},
    {"name": "Eesti PäikeseVägi OÜ", "search_terms": ["PäikeseVägi", "Paikesevagi"], "company_id": 9409},
    {"name": "AQ Components Kodara OÜ", "search_terms": ["AQ Components Kodara"], "company_id": 531},
    {"name": "Topbox Oy", "search_terms": ["Topbox"], "company_id": 451},
    {"name": "SKELETON TECHNOLOGIES OÜ", "search_terms": ["Skeleton Technologies"], "company_id": 3186},
    {"name": "Silikaat AS", "search_terms": ["Silikaat"], "company_id": 11336},
    {"name": "Tallinna Linnatransport AS", "search_terms": ["Tallinna Linnatransport", "TLT"], "company_id": 11904},
    {"name": "Starship Technologies OÜ", "search_terms": ["Starship Technologies", "Starship"], "company_id": 2145},
    {"name": "OÜ TKV Ehitus", "search_terms": ["TKV Ehitus"], "company_id": 1142},
    {"name": "Demeca Biokaasu Oy", "search_terms": ["Demeca Biokaasu", "Demeca"], "company_id": 317},
    
    # Lower tier (€100-€1K GP) - Still worth monitoring
    {"name": "MultiCharge OÜ", "search_terms": ["MultiCharge"], "company_id": 5747},
    {"name": "Tamult Tootmine OÜ", "search_terms": ["Tamult"], "company_id": 13422},
    {"name": "TSG Nordic Gas OÜ", "search_terms": ["TSG Nordic Gas"], "company_id": 10961},
    {"name": "MyPack OÜ", "search_terms": ["MyPack"], "company_id": 9606},
    {"name": "Trade Builder Baltic OÜ", "search_terms": ["Trade Builder Baltic"], "company_id": 6800},
    {"name": "P-Tech OÜ", "search_terms": ["P-Tech"], "company_id": 9113},
    {"name": "ECOSTEEL PRO OÜ", "search_terms": ["ECOSTEEL PRO", "Ecosteel"], "company_id": 899},
    {"name": "K.Met AS", "search_terms": ["K.Met"], "company_id": 4652},
    {"name": "Cleveron AS", "search_terms": ["Cleveron"], "company_id": 4374},
    {"name": "Nordic Armoury OÜ", "search_terms": ["Nordic Armoury"], "company_id": 1532},
    {"name": "TERGEN GRUPP OÜ", "search_terms": ["TERGEN GRUPP", "Tergen"], "company_id": 6024},
    {"name": "10Lines OÜ", "search_terms": ["10Lines"], "company_id": 242},
    {"name": "Aiameister OÜ", "search_terms": ["Aiameister"], "company_id": 1294},
    {"name": "Kruuli trükikoja OÜ", "search_terms": ["Kruuli trükikoda", "Kruuli"], "company_id": 11700},
    {"name": "COMODULE OÜ", "search_terms": ["COMODULE", "Comodule"], "company_id": 323},
    {"name": "Monitoimi Lätti", "search_terms": ["Monitoimi"], "company_id": 10988},
    {"name": "LTH-Baas Germany", "search_terms": ["LTH-Baas"], "company_id": 10704},
]

# Estonian news RSS feeds (priority sources)
ESTONIAN_RSS_FEEDS = [
    # Major Estonian business news
    {"name": "ERR Business", "url": "https://www.err.ee/rss/majandus"},
    {"name": "Postimees Business", "url": "https://majandus.postimees.ee/rss"},
    {"name": "Delfi Business", "url": "https://www.delfi.ee/rss/majandus"},
    {"name": "Äripäev", "url": "https://www.aripaev.ee/rss"},
    
    # Industry-specific (Äripäev network)
    {"name": "Tööstusuudised", "url": "https://www.toostusuudised.ee/rss"},
    {"name": "Logistikauudised", "url": "https://www.logistikauudised.ee/rss"},
    {"name": "Ehitusuudised", "url": "https://www.ehitusuudised.ee/rss"},
    
    # Tech news
    {"name": "Geenius", "url": "https://geenius.ee/feed/"},
    {"name": "Digigeenius", "url": "https://digi.geenius.ee/feed/"},
    
    # Regional news
    {"name": "ERR Eesti", "url": "https://www.err.ee/rss/eesti"},
]

# ============================================================================
# NEWS API CLIENT - International news via NewsAPI.org
# ============================================================================

def search_newsapi(query: str, from_date: str, api_key: str) -> list:
    """
    Search NewsAPI.org for articles mentioning the query.
    Free tier: 100 requests/day, articles up to 1 month old.
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{query}"',  # Exact phrase match
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",  # English articles
        "pageSize": 5,
        "apiKey": api_key,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "url": article.get("url", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published": article.get("publishedAt", ""),
                "region": "International",
            })
        return articles
    except Exception as e:
        print(f"NewsAPI error for '{query}': {e}")
        return []

# ============================================================================
# ESTONIAN RSS PARSER - Priority Estonian news sources
# ============================================================================

def search_estonian_rss(search_terms: list, hours_back: int = 48) -> list:
    """
    Search Estonian RSS feeds for mentions of the company.
    Checks article titles and descriptions.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    found_articles = []
    
    for feed_config in ESTONIAN_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            
            for entry in feed.entries[:50]:  # Check last 50 entries per feed
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                
                # Skip old articles
                if pub_date and pub_date < cutoff_time:
                    continue
                
                # Search for company mentions
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                content = f"{title} {summary}".lower()
                
                for term in search_terms:
                    if term.lower() in content:
                        found_articles.append({
                            "title": title,
                            "description": summary[:200] + "..." if len(summary) > 200 else summary,
                            "url": entry.get("link", ""),
                            "source": feed_config["name"],
                            "published": pub_date.isoformat() if pub_date else "",
                            "region": "Estonia 🇪🇪",
                            "matched_term": term,
                        })
                        break  # Don't duplicate for multiple term matches
                        
        except Exception as e:
            print(f"RSS feed error for {feed_config['name']}: {e}")
            continue
    
    return found_articles

# ============================================================================
# SLACK NOTIFICATION
# ============================================================================

def send_slack_notification(webhook_url: str, customer: dict, articles: list):
    """
    Send a formatted Slack message about news mentions.
    """
    if not articles:
        return
    
    # Build message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 News Alert: {customer['name']}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Found *{len(articles)} article(s)* mentioning your customer"
                }
            ]
        },
        {"type": "divider"}
    ]
    
    # Add article blocks (limit to 5 to avoid message size limits)
    for article in articles[:5]:
        region_emoji = "🇪🇪" if "Estonia" in article.get("region", "") else "🌍"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{article['url']}|{article['title']}>*\n{region_emoji} {article['source']}"
            }
        })
        
        if article.get("description"):
            # Clean HTML tags from description
            clean_desc = re.sub('<[^<]+?>', '', article["description"])
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": clean_desc[:300]}]
            })
    
    # Add footer with timestamp
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn", 
                "text": f"🤖 Automated news monitor | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            }
        ]
    })
    
    payload = {"blocks": blocks}
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Slack notification sent for {customer['name']}")
    except Exception as e:
        print(f"Slack notification failed: {e}")

# ============================================================================
# MAIN FUNCTION - Entry point for Cloud Function
# ============================================================================

def monitor_customer_news(request=None):
    """
    Main entry point. Can be triggered by:
    - HTTP request (Cloud Function)
    - Scheduled trigger (Cloud Scheduler)
    - Manual execution
    """
    # Load configuration from environment
    news_api_key = os.environ.get("NEWS_API_KEY")
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        return {"error": "SLACK_WEBHOOK_URL not configured"}, 500
    
    # Calculate date range (last 2 days for daily runs)
    from_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    
    total_articles_found = 0
    customers_with_news = []
    
    print(f"Starting news scan for {len(CUSTOMERS)} customers...")
    
    for customer in CUSTOMERS:
        all_articles = []
        
        # 1. Priority: Search Estonian RSS feeds
        print(f"Scanning Estonian news for {customer['name']}...")
        estonian_articles = search_estonian_rss(customer["search_terms"])
        all_articles.extend(estonian_articles)
        
        # 2. Secondary: Search international news (if API key provided)
        # Note: Limited to top customers due to API rate limits
        if news_api_key and customer.get("company_id") in [4622, 3214, 847, 5791, 372, 931, 7064, 338]:
            print(f"Scanning international news for {customer['name']}...")
            for term in customer["search_terms"][:1]:  # Only first term to save API calls
                intl_articles = search_newsapi(term, from_date, news_api_key)
                all_articles.extend(intl_articles)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                unique_articles.append(article)
        
        # Send notification if articles found
        if unique_articles:
            send_slack_notification(slack_webhook_url, customer, unique_articles)
            total_articles_found += len(unique_articles)
            customers_with_news.append(customer["name"])
    
    # Send summary if no news found
    if total_articles_found == 0:
        summary_payload = {
            "text": f"📰 Daily news scan complete — no mentions found for your {len(CUSTOMERS)} monitored customers."
        }
        requests.post(slack_webhook_url, json=summary_payload)
    
    result = {
        "status": "success",
        "customers_scanned": len(CUSTOMERS),
        "articles_found": total_articles_found,
        "customers_with_news": customers_with_news,
        "scan_time": datetime.utcnow().isoformat()
    }
    
    print(f"Scan complete: {result}")
    return result, 200


# ============================================================================
# LOCAL TESTING
# ============================================================================

if __name__ == "__main__":
    # For local testing, set environment variables first:
    # export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxx/xxx/xxx"
    # export NEWS_API_KEY="your-newsapi-key"  # Optional
    
    result, status = monitor_customer_news()
    print(json.dumps(result, indent=2))
