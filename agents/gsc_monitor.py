#!/usr/bin/env python3
"""
GSC Performance Monitor - Weekly SEO optimization agent.

What it does:
1. Pulls last 90 days of data from Google Search Console API
2. Finds pages ranking positions 11-20 (page 2 - close to page 1)
3. Finds pages with high impressions but low CTR (title/meta problem)
4. Uses Claude to generate improved title + meta description for each
5. Auto-applies changes to HTML files
6. Sends Telegram report with all changes made

Setup (one-time):
- Create a Google Cloud service account with Search Console API access
- Add service account email as a user in GSC
- Add the JSON key as GitHub secret: GSC_SERVICE_ACCOUNT_JSON
- Add secret: GSC_SITE_URL (e.g. sc-domain:makeinvoice.online)

Usage:
  python agents/gsc_monitor.py          # Run full optimization
  python agents/gsc_monitor.py --report # Report only, no changes applied
"""

import os
import re
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GSC_SERVICE_ACCOUNT_JSON = os.environ.get('GSC_SERVICE_ACCOUNT_JSON')
GSC_SITE_URL = os.environ.get('GSC_SITE_URL', 'sc-domain:makeinvoice.online')

SITE_URL = 'https://www.makeinvoice.online'
BASE_DIR = Path(__file__).parent.parent
BLOG_DIR = BASE_DIR / 'blog'

# Thresholds
PAGE2_MIN = 11.0
PAGE2_MAX = 20.0
LOW_CTR_MIN_IMPRESSIONS = 200
LOW_CTR_MAX_CTR = 0.03       # 3% — anything below this with 200+ impressions is a candidate
MAX_PAGES_TO_OPTIMIZE = 5    # Cap per run to keep costs low


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram] {message}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        print(f"Telegram error: {e}")


# ---------------------------------------------------------------------------
# Google Auth (JWT-based, no external google-auth library needed)
# ---------------------------------------------------------------------------

def get_access_token(service_account_info: dict) -> str:
    """Exchange service account credentials for a Bearer token using JWT."""
    import base64
    import struct
    import hashlib
    import hmac

    # We need RSA signing — use cryptography library
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend

    now = int(time.time())
    claim_set = {
        "iss": service_account_info["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600,
        "iat": now,
    }

    def b64(data):
        if isinstance(data, str):
            data = data.encode()
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

    header = b64(json.dumps({"alg": "RS256", "typ": "JWT"}))
    payload = b64(json.dumps(claim_set))
    signing_input = f"{header}.{payload}".encode()

    private_key = serialization.load_pem_private_key(
        service_account_info["private_key"].encode(),
        password=None,
        backend=default_backend(),
    )
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    jwt_token = f"{header}.{payload}.{b64(signature)}"

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# GSC API
# ---------------------------------------------------------------------------

def fetch_search_analytics(token: str, days: int = 90) -> list:
    """
    Pull search analytics grouped by page for the last N days.
    Returns list of {page, clicks, impressions, ctr, position}.
    """
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{requests.utils.quote(GSC_SITE_URL, safe='')}/searchAnalytics/query"

    payload = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
        "rowLimit": 500,
    }

    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json().get("rows", [])

    results = []
    for row in rows:
        results.append({
            "page": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": row["ctr"],
            "position": row["position"],
        })
    return results


# ---------------------------------------------------------------------------
# Candidate detection
# ---------------------------------------------------------------------------

def find_page2_candidates(rows: list) -> list:
    """Pages ranking 11-20: close to page 1, worth a push."""
    candidates = [
        r for r in rows
        if PAGE2_MIN <= r["position"] <= PAGE2_MAX
        and r["impressions"] >= 50          # Has some visibility
        and "/blog/" in r["page"]           # Blog posts only
    ]
    return sorted(candidates, key=lambda r: r["impressions"], reverse=True)


def find_low_ctr_candidates(rows: list) -> list:
    """Pages with lots of impressions but low CTR: title/meta problem."""
    candidates = [
        r for r in rows
        if r["impressions"] >= LOW_CTR_MIN_IMPRESSIONS
        and r["ctr"] < LOW_CTR_MAX_CTR
        and "/blog/" in r["page"]
    ]
    return sorted(candidates, key=lambda r: r["impressions"], reverse=True)


def deduplicate(page2: list, low_ctr: list) -> list:
    """Merge both lists, tag each with reason, avoid duplicates."""
    seen = set()
    combined = []
    for r in page2:
        if r["page"] not in seen:
            seen.add(r["page"])
            combined.append({**r, "reason": "page2"})
    for r in low_ctr:
        if r["page"] not in seen:
            seen.add(r["page"])
            combined.append({**r, "reason": "low_ctr"})
        else:
            # Already in list as page2 — upgrade reason
            for item in combined:
                if item["page"] == r["page"]:
                    item["reason"] = "page2+low_ctr"
    return combined[:MAX_PAGES_TO_OPTIMIZE]


# ---------------------------------------------------------------------------
# URL → local file mapping
# ---------------------------------------------------------------------------

def url_to_filepath(page_url: str) -> Path | None:
    """Convert a GSC page URL to a local HTML file path."""
    # Strip site prefix
    path = page_url.replace(SITE_URL, "").lstrip("/")

    if not path:
        return BASE_DIR / "index.html"

    # Try exact .html match
    candidate = BASE_DIR / f"{path}.html"
    if candidate.exists():
        return candidate

    # Try as directory index
    candidate = BASE_DIR / path / "index.html"
    if candidate.exists():
        return candidate

    # Already has .html
    candidate = BASE_DIR / path
    if candidate.exists():
        return candidate

    return None


# ---------------------------------------------------------------------------
# HTML meta extraction & update
# ---------------------------------------------------------------------------

def extract_meta(html: str) -> dict:
    title_m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    desc_m = re.search(r'<meta name="description" content="(.*?)"', html)
    return {
        "title": title_m.group(1).strip() if title_m else "",
        "description": desc_m.group(1).strip() if desc_m else "",
    }


def apply_meta_updates(html: str, new_title: str, new_desc: str) -> str:
    """Update title, meta description, og:title, og:description, twitter tags."""
    # <title>
    html = re.sub(r'<title>.*?</title>', f'<title>{new_title}</title>', html, flags=re.DOTALL)
    # meta description
    html = re.sub(
        r'(<meta name="description" content=")[^"]*(")',
        rf'\g<1>{new_desc}\2', html
    )
    # og:title
    html = re.sub(
        r'(<meta property="og:title" content=")[^"]*(")',
        rf'\g<1>{new_title}\2', html
    )
    # og:description
    html = re.sub(
        r'(<meta property="og:description" content=")[^"]*(")',
        rf'\g<1>{new_desc}\2', html
    )
    # twitter:title
    html = re.sub(
        r'(<meta name="twitter:title" content=")[^"]*(")',
        rf'\g<1>{new_title}\2', html
    )
    # twitter:description
    html = re.sub(
        r'(<meta name="twitter:description" content=")[^"]*(")',
        rf'\g<1>{new_desc}\2', html
    )
    return html


# ---------------------------------------------------------------------------
# Claude: generate improved title + meta
# ---------------------------------------------------------------------------

def generate_improvements(page: dict, current_meta: dict) -> dict | None:
    """Ask Claude Haiku to suggest a better title and meta description."""
    if not ANTHROPIC_API_KEY:
        print("  ⚠️  No ANTHROPIC_API_KEY — skipping")
        return None

    reason_text = {
        "page2": f"ranking position {page['position']:.1f} (page 2) — needs a content/relevance boost",
        "low_ctr": f"only {page['ctr']*100:.1f}% CTR despite {page['impressions']} impressions — title/meta isn't compelling",
        "page2+low_ctr": f"ranking position {page['position']:.1f} AND only {page['ctr']*100:.1f}% CTR — both issues",
    }.get(page["reason"], "")

    prompt = f"""You are an SEO expert. Improve the title and meta description for this page.

Page URL: {page['page']}
Current title: {current_meta['title']}
Current meta description: {current_meta['description']}

GSC data: {reason_text}
Clicks: {page['clicks']} | Impressions: {page['impressions']} | Position: {page['position']:.1f}

Rules:
- Title: max 60 chars, include primary keyword near the start, make it compelling
- Meta description: max 155 chars, include a clear benefit + call to action
- Keep the same topic/keyword focus — do NOT change what the page is about
- Make it more click-worthy without being clickbait

Return ONLY valid JSON:
{{"title": "New title here", "description": "New meta description here"}}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            json_m = re.search(r'\{.*\}', text, re.DOTALL)
            if json_m:
                return json.loads(json_m.group())
    except Exception as e:
        print(f"  ❌ Claude error: {e}")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    report_only = "--report" in sys.argv

    print("📊 GSC Performance Monitor starting...\n")

    # Load service account
    if not GSC_SERVICE_ACCOUNT_JSON:
        print("❌ GSC_SERVICE_ACCOUNT_JSON not set. See setup instructions in docstring.")
        sys.exit(1)

    try:
        service_account_info = json.loads(GSC_SERVICE_ACCOUNT_JSON)
    except json.JSONDecodeError:
        print("❌ GSC_SERVICE_ACCOUNT_JSON is not valid JSON.")
        sys.exit(1)

    # Authenticate
    print("🔑 Authenticating with Google...")
    try:
        token = get_access_token(service_account_info)
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        sys.exit(1)

    # Fetch data
    print("📥 Fetching last 90 days from Search Console...")
    try:
        rows = fetch_search_analytics(token)
    except Exception as e:
        print(f"❌ GSC API error: {e}")
        sys.exit(1)

    print(f"   {len(rows)} pages found in GSC data\n")

    # Find candidates
    page2 = find_page2_candidates(rows)
    low_ctr = find_low_ctr_candidates(rows)
    candidates = deduplicate(page2, low_ctr)

    print(f"🎯 Page 2 candidates (pos 11-20): {len(page2)}")
    print(f"📉 Low CTR candidates (>{LOW_CTR_MIN_IMPRESSIONS} impr, <{LOW_CTR_MAX_CTR*100:.0f}% CTR): {len(low_ctr)}")
    print(f"✏️  Pages to optimize this run: {len(candidates)}\n")

    if not candidates:
        msg = "📊 *GSC Monitor*: No optimization candidates found this week. All pages look healthy!"
        print(msg)
        send_telegram(msg)
        return

    # Process each candidate
    changes = []
    for page in candidates:
        url = page["page"]
        print(f"  [{page['reason'].upper()}] {url}")
        print(f"    Position: {page['position']:.1f} | CTR: {page['ctr']*100:.1f}% | Impressions: {page['impressions']}")

        filepath = url_to_filepath(url)
        if not filepath:
            print(f"    ⚠️  Local file not found — skipping\n")
            continue

        html = filepath.read_text(encoding='utf-8')
        current_meta = extract_meta(html)
        print(f"    Title: {current_meta['title'][:70]}")

        improvement = generate_improvements(page, current_meta)
        if not improvement:
            print(f"    ⚠️  No improvement generated — skipping\n")
            continue

        print(f"    → New title: {improvement['title']}")
        print(f"    → New desc:  {improvement['description'][:80]}...")

        if not report_only:
            updated_html = apply_meta_updates(html, improvement["title"], improvement["description"])
            filepath.write_text(updated_html, encoding='utf-8')
            print(f"    ✅ Applied\n")
        else:
            print(f"    👁  Report only — not applied\n")

        changes.append({
            "url": url,
            "reason": page["reason"],
            "position": page["position"],
            "ctr": page["ctr"],
            "impressions": page["impressions"],
            "old_title": current_meta["title"],
            "new_title": improvement["title"],
            "old_desc": current_meta["description"],
            "new_desc": improvement["description"],
            "applied": not report_only,
        })

    # Telegram report
    if changes:
        action = "applied" if not report_only else "suggested (report only)"
        msg = f"📊 *GSC Performance Monitor*\n\n"
        msg += f"✏️ {len(changes)} optimizations {action}:\n\n"
        for c in changes:
            reason_label = {"page2": "Page 2", "low_ctr": "Low CTR", "page2+low_ctr": "Page 2 + Low CTR"}.get(c["reason"], c["reason"])
            short_url = c["url"].replace(SITE_URL, "")
            msg += f"*{short_url}*\n"
            msg += f"  Reason: {reason_label} | Pos: {c['position']:.1f} | CTR: {c['ctr']*100:.1f}%\n"
            msg += f"  Was: _{c['old_title'][:50]}_\n"
            msg += f"  Now: _{c['new_title'][:50]}_\n\n"
        send_telegram(msg)

    print(f"\n✅ GSC Monitor complete. {len(changes)} pages optimized.")


if __name__ == "__main__":
    main()
