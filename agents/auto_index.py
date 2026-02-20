#!/usr/bin/env python3
"""
Auto-Index Agent - Automatically submits new URLs to search engines.

Supports:
- Google (sitemap ping)
- Bing/Yandex (IndexNow protocol)

Runs after Content Engine to ensure new content gets indexed quickly.
"""

import os
import sys
import json
import hashlib
import requests
from datetime import datetime
from pathlib import Path

# Configuration
SITE_URL = "https://www.makeinvoice.online"
SITEMAP_URL = f"{SITE_URL}/sitemap.xml"
INDEXNOW_KEY = os.environ.get('INDEXNOW_KEY', 'makeinvoice-indexnow-key')

# Telegram notifications
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Directories
BASE_DIR = Path(__file__).parent.parent
TRACKING_FILE = BASE_DIR / 'agents' / '.indexed_urls.json'


def send_telegram(message: str):
    """Send notification to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Telegram not configured. Message: {message}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram: {e}")


def load_indexed_urls() -> set:
    """Load previously indexed URLs."""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('urls', []))
    return set()


def save_indexed_urls(urls: set):
    """Save indexed URLs."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        json.dump({
            'urls': list(urls),
            'last_updated': datetime.now().isoformat()
        }, f, indent=2)


def get_urls_from_sitemap() -> list:
    """Extract all URLs from sitemap."""
    try:
        response = requests.get(SITEMAP_URL, timeout=30)
        response.raise_for_status()

        # Simple XML parsing for <loc> tags
        import re
        urls = re.findall(r'<loc>(.*?)</loc>', response.text)
        return urls
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []


def ping_google_sitemap():
    """Ping Google to re-crawl sitemap."""
    ping_url = f"https://www.google.com/ping?sitemap={SITEMAP_URL}"
    try:
        response = requests.get(ping_url, timeout=30)
        if response.status_code == 200:
            print("✅ Google sitemap ping successful")
            return True
        else:
            print(f"⚠️ Google ping returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Google ping failed: {e}")
        return False


def ping_bing_sitemap():
    """Ping Bing to re-crawl sitemap."""
    ping_url = f"https://www.bing.com/ping?sitemap={SITEMAP_URL}"
    try:
        response = requests.get(ping_url, timeout=30)
        if response.status_code == 200:
            print("✅ Bing sitemap ping successful")
            return True
        else:
            print(f"⚠️ Bing ping returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bing ping failed: {e}")
        return False


def submit_indexnow(urls: list):
    """Submit URLs to IndexNow (Bing, Yandex, Seznam, Naver)."""
    if not urls:
        print("No URLs to submit to IndexNow")
        return False

    # IndexNow API endpoint (using Bing's endpoint)
    api_url = "https://api.indexnow.org/indexnow"

    payload = {
        "host": "www.makeinvoice.online",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls[:100]  # Max 100 URLs per request
    }

    try:
        response = requests.post(
            api_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code in [200, 202]:
            print(f"✅ IndexNow: Submitted {len(urls)} URLs successfully")
            return True
        elif response.status_code == 422:
            print("⚠️ IndexNow: Key validation failed (need to create key file)")
            return False
        else:
            print(f"⚠️ IndexNow returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ IndexNow submission failed: {e}")
        return False


def find_new_urls() -> list:
    """Find URLs that haven't been indexed yet."""
    all_urls = get_urls_from_sitemap()
    indexed_urls = load_indexed_urls()

    new_urls = [url for url in all_urls if url not in indexed_urls]
    return new_urls


def main():
    """Main entry point."""
    print("🔍 Auto-Index Agent Starting...")

    # Get new URLs
    new_urls = find_new_urls()
    all_urls = get_urls_from_sitemap()

    print(f"📊 Total URLs in sitemap: {len(all_urls)}")
    print(f"🆕 New URLs to index: {len(new_urls)}")

    if new_urls:
        print("\nNew URLs found:")
        for url in new_urls[:10]:  # Show first 10
            print(f"  • {url}")
        if len(new_urls) > 10:
            print(f"  ... and {len(new_urls) - 10} more")

    # Ping search engines
    print("\n📡 Pinging search engines...")
    google_ok = ping_google_sitemap()
    bing_ok = ping_bing_sitemap()

    # Submit new URLs to IndexNow
    indexnow_ok = False
    if new_urls:
        print(f"\n🚀 Submitting {len(new_urls)} new URLs to IndexNow...")
        indexnow_ok = submit_indexnow(new_urls)

    # Update tracking
    if new_urls:
        indexed_urls = load_indexed_urls()
        indexed_urls.update(new_urls)
        save_indexed_urls(indexed_urls)
        print(f"\n💾 Updated tracking file with {len(new_urls)} new URLs")

    # Send Telegram summary
    summary = "🔍 *Auto-Index Agent Complete*\n\n"
    summary += f"📊 Total URLs: {len(all_urls)}\n"
    summary += f"🆕 New URLs: {len(new_urls)}\n\n"
    summary += f"*Search Engine Pings:*\n"
    summary += f"• Google: {'✅' if google_ok else '❌'}\n"
    summary += f"• Bing: {'✅' if bing_ok else '❌'}\n"
    if new_urls:
        summary += f"• IndexNow: {'✅' if indexnow_ok else '❌'}\n"
        summary += f"\n*New URLs submitted:*\n"
        for url in new_urls[:5]:
            # Shorten URL for display
            short_url = url.replace('https://www.makeinvoice.online', '')
            summary += f"• {short_url}\n"
        if len(new_urls) > 5:
            summary += f"_...and {len(new_urls) - 5} more_"

    send_telegram(summary)
    print("\n✅ Auto-Index Agent Complete!")


if __name__ == '__main__':
    main()
