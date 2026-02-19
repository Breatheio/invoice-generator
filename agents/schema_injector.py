#!/usr/bin/env python3
"""
Schema Injector - Adds FAQ JSON-LD schema to blog posts.

What it does:
1. Scans all blog HTML files (or a single file if passed as argument)
2. Fixes mainEntityOfPage URL (.html bug) in existing Article schema
3. Extracts FAQ Q&As from existing FAQ sections in the HTML
4. For posts without FAQs, uses Claude to generate 5 Q&As and adds them to the page
5. Injects FAQPage JSON-LD schema into <head>
6. Skips posts that already have FAQ schema

Usage:
  python agents/schema_injector.py               # Process all blog posts
  python agents/schema_injector.py blog/foo.html # Process a single file
"""

import os
import re
import json
import sys
import requests
from pathlib import Path
from datetime import datetime

# Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
SITE_URL = "https://www.makeinvoice.online"

BASE_DIR = Path(__file__).parent.parent
BLOG_DIR = BASE_DIR / 'blog'


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
            timeout=10
        )
    except Exception as e:
        print(f"Telegram error: {e}")


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------

def extract_meta(html: str) -> dict:
    """Extract title, description, canonical URL and datePublished from HTML."""
    title_m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    desc_m = re.search(r'<meta name="description" content="(.*?)"', html)
    canonical_m = re.search(r'<link rel="canonical" href="(.*?)"', html)
    date_m = re.search(r'"datePublished":\s*"([\d-]+)"', html)

    return {
        'title': title_m.group(1).strip() if title_m else '',
        'description': desc_m.group(1).strip() if desc_m else '',
        'canonical': canonical_m.group(1).strip() if canonical_m else '',
        'date_published': date_m.group(1).strip() if date_m else datetime.now().strftime('%Y-%m-%d'),
    }


def extract_faqs(html: str) -> list:
    """
    Extract FAQ Q&A pairs from an existing 'Frequently Asked Questions' section.
    Looks for h3 questions + p answers that follow a FAQ h2 heading.
    """
    faq_m = re.search(
        r'<h2[^>]*>.*?(?:Frequently Asked Questions|FAQ).*?</h2>(.*)',
        html, re.DOTALL | re.IGNORECASE
    )
    if not faq_m:
        return []

    faq_section = faq_m.group(1)
    faqs = []
    for m in re.finditer(r'<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>', faq_section, re.DOTALL):
        question = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        answer = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if question and answer:
            faqs.append({'question': question, 'answer': answer})

    return faqs[:10]


def has_faq_schema(html: str) -> bool:
    return 'FAQPage' in html


def fix_article_schema_url(html: str) -> tuple:
    """
    Remove .html from mainEntityOfPage @id URLs in existing Article schema.
    Returns (new_html, was_changed).
    """
    fixed = re.sub(
        r'("mainEntityOfPage":\s*\{[^}]*"@id":\s*"https://[^"]+?)\.html(")',
        r'\1\2',
        html
    )
    return fixed, fixed != html


# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------

def generate_faqs_with_claude(title: str, description: str) -> list:
    """Generate 5 FAQ Q&A pairs using Claude Haiku."""
    if not ANTHROPIC_API_KEY:
        print("  ⚠️  No ANTHROPIC_API_KEY — skipping FAQ generation")
        return []

    prompt = (
        f"Generate 5 frequently asked questions with concise answers for this blog article.\n\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        f"Return ONLY a JSON array:\n"
        f'[{{"question": "...", "answer": "..."}}, ...]\n\n'
        f"Rules:\n"
        f"- Questions must be real things users search for\n"
        f"- Answers: 2-4 sentences, factual and helpful\n"
        f"- No markdown, no extra text — just valid JSON"
    )

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
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            text = resp.json()['content'][0]['text'].strip()
            json_m = re.search(r'\[.*\]', text, re.DOTALL)
            if json_m:
                return json.loads(json_m.group())
    except Exception as e:
        print(f"  ❌ Claude error: {e}")

    return []


# ---------------------------------------------------------------------------
# Schema building & injection
# ---------------------------------------------------------------------------

def build_faq_schema(faqs: list) -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq['question'],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq['answer'],
                },
            }
            for faq in faqs
        ],
    }
    return json.dumps(schema, indent=2, ensure_ascii=False)


def inject_faq_schema(html: str, faqs: list) -> str:
    """Insert FAQPage JSON-LD script block before </head>."""
    schema_block = (
        '\n  <!-- JSON-LD FAQ Schema -->\n'
        '  <script type="application/ld+json">\n'
        f'  {build_faq_schema(faqs)}\n'
        '  </script>'
    )
    return html.replace('</head>', f'{schema_block}\n</head>', 1)


def build_faq_html(faqs: list) -> str:
    """Build the HTML for a FAQ section to insert into the page body."""
    lines = [
        '\n  <!-- FAQ Section (auto-generated) -->',
        '  <section class="mt-12 mb-8">',
        '    <h2 class="text-2xl font-bold text-gray-900 mt-8 mb-4">Frequently Asked Questions</h2>',
    ]
    for faq in faqs:
        q = faq['question'].replace('<', '&lt;').replace('>', '&gt;')
        a = faq['answer'].replace('<', '&lt;').replace('>', '&gt;')
        lines.append(f'    <h3 class="text-xl font-semibold text-gray-900 mt-6 mb-3">{q}</h3>')
        lines.append(f'    <p class="text-gray-600 mb-4">{a}</p>')
    lines.append('  </section>')
    return '\n'.join(lines)


def add_faq_section_to_body(html: str, faqs: list) -> str:
    """Insert a FAQ section before </article> (fallback: before </main>)."""
    faq_html = build_faq_html(faqs)
    if '</article>' in html:
        return html.replace('</article>', f'{faq_html}\n  </article>', 1)
    return html.replace('</main>', f'{faq_html}\n  </main>', 1)


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_file(filepath: Path) -> dict:
    html = filepath.read_text(encoding='utf-8')
    changes = []
    modified = False

    # 1. Fix mainEntityOfPage .html URL bug
    html, url_fixed = fix_article_schema_url(html)
    if url_fixed:
        modified = True
        changes.append('fixed mainEntityOfPage URL (.html removed)')

    # 2. Skip if FAQ schema already present
    if has_faq_schema(html):
        changes.append('FAQ schema already present — skipped')
        if modified:
            filepath.write_text(html, encoding='utf-8')
        return {'file': filepath.name, 'changes': changes, 'faq_injected': False}

    # 3. Extract existing FAQs from HTML content
    faqs = extract_faqs(html)

    # 4. If no FAQs found, generate with Claude and add to body
    generated = False
    if not faqs:
        meta = extract_meta(html)
        print(f"  🤖 Generating FAQs via Claude...")
        faqs = generate_faqs_with_claude(meta['title'], meta['description'])
        if faqs:
            html = add_faq_section_to_body(html, faqs)
            generated = True
            changes.append(f'generated {len(faqs)} FAQs via Claude + added to body')

    # 5. Inject FAQ schema into <head>
    if faqs:
        html = inject_faq_schema(html, faqs)
        modified = True
        source = 'generated' if generated else 'extracted'
        changes.append(f'injected FAQPage schema ({len(faqs)} Q&As, {source})')
    else:
        changes.append('no FAQs found or generated — schema not injected')

    if modified:
        filepath.write_text(html, encoding='utf-8')

    return {'file': filepath.name, 'changes': changes, 'faq_injected': bool(faqs)}


def main():
    # Support single-file mode: python schema_injector.py blog/foo.html
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.is_absolute():
            target = BASE_DIR / target
        if not target.exists():
            print(f"❌ File not found: {target}")
            sys.exit(1)
        files = [target]
    else:
        files = sorted(f for f in BLOG_DIR.glob('*.html') if f.name != 'index.html')

    print(f"🔧 Schema Injector — processing {len(files)} file(s)\n")

    results = []
    for fp in files:
        print(f"  [{fp.name}]")
        result = process_file(fp)
        results.append(result)
        for c in result['changes']:
            print(f"    ✓ {c}")

    injected = sum(1 for r in results if r['faq_injected'])
    generated = sum(1 for r in results if any('generated' in c for c in r['changes']))
    url_fixed = sum(1 for r in results if any('fixed' in c for c in r['changes']))
    skipped = sum(1 for r in results if any('already present' in c for c in r['changes']))

    print(f"\n✅ Done!")
    print(f"   FAQ schema injected : {injected}")
    print(f"   FAQs generated      : {generated}")
    print(f"   URLs fixed          : {url_fixed}")
    print(f"   Already had schema  : {skipped}")

    msg = (
        f"🔧 *Schema Injector Complete*\n\n"
        f"📄 Files processed: {len(files)}\n"
        f"✅ FAQ schema injected: {injected}\n"
        f"🤖 FAQs generated by Claude: {generated}\n"
        f"🔗 mainEntityOfPage URLs fixed: {url_fixed}\n"
        f"⏭ Already had schema: {skipped}"
    )
    send_telegram(msg)


if __name__ == '__main__':
    main()
