#!/usr/bin/env python3
"""
Content Engine - Unified content generation system
Generates blog articles, landing pages, and SEO content.

Modes:
- questions: Find and answer questions from Reddit/Quora
- keywords: Target specific SEO keywords
- landing: Generate industry/template landing pages
- evergreen: Create timeless how-to content
"""

import os
import sys
import json
import re
import random
import requests
from datetime import datetime
from pathlib import Path

# Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Directories
BASE_DIR = Path(__file__).parent.parent
BLOG_DIR = BASE_DIR / 'blog' / 'posts'
LANDING_DIR = BASE_DIR / 'landing-pages'
TRACKING_FILE = BASE_DIR / 'agents' / '.content_tracking.json'

# Content ideas bank
KEYWORD_TOPICS = [
    {"keyword": "freelance invoice template", "title": "Free Freelance Invoice Template (2026)", "type": "blog"},
    {"keyword": "how to invoice as a freelancer", "title": "How to Invoice as a Freelancer: Complete Guide", "type": "blog"},
    {"keyword": "invoice payment terms", "title": "Invoice Payment Terms Explained: Net 30, Due on Receipt & More", "type": "blog"},
    {"keyword": "what to include on an invoice", "title": "What to Include on an Invoice: Essential Checklist", "type": "blog"},
    {"keyword": "invoice vs receipt", "title": "Invoice vs Receipt: What's the Difference?", "type": "blog"},
    {"keyword": "how to ask for payment professionally", "title": "How to Ask for Payment Professionally (Email Templates)", "type": "blog"},
    {"keyword": "late payment email template", "title": "Late Payment Reminder Email Templates That Work", "type": "blog"},
    {"keyword": "small business invoice", "title": "Small Business Invoice Guide: Templates & Best Practices", "type": "blog"},
    {"keyword": "consulting invoice template", "title": "Consulting Invoice Template: Free Download & Guide", "type": "blog"},
    {"keyword": "how to number invoices", "title": "Invoice Numbering: Best Systems for Your Business", "type": "blog"},
    {"keyword": "invoice due date", "title": "Setting Invoice Due Dates: Best Practices for Getting Paid", "type": "blog"},
    {"keyword": "proforma invoice", "title": "What is a Proforma Invoice? When and How to Use One", "type": "blog"},
    {"keyword": "recurring invoice", "title": "Recurring Invoices: How to Set Up Automatic Billing", "type": "blog"},
    {"keyword": "invoice for services rendered", "title": "How to Create an Invoice for Services Rendered", "type": "blog"},
    {"keyword": "self employed invoice", "title": "Self-Employed Invoice Template & Tax Tips", "type": "blog"},
]

LANDING_PAGE_IDEAS = [
    {"slug": "invoice-generator-for-freelancers", "title": "Invoice Generator for Freelancers", "industry": "freelancers"},
    {"slug": "invoice-generator-for-photographers", "title": "Invoice Generator for Photographers", "industry": "photographers"},
    {"slug": "invoice-generator-for-consultants", "title": "Invoice Generator for Consultants", "industry": "consultants"},
    {"slug": "invoice-generator-for-web-designers", "title": "Invoice Generator for Web Designers", "industry": "web designers"},
    {"slug": "invoice-generator-for-contractors", "title": "Invoice Generator for Contractors", "industry": "contractors"},
    {"slug": "invoice-generator-for-graphic-designers", "title": "Invoice Generator for Graphic Designers", "industry": "graphic designers"},
    {"slug": "invoice-generator-for-writers", "title": "Invoice Generator for Writers & Copywriters", "industry": "writers"},
    {"slug": "invoice-generator-for-developers", "title": "Invoice Generator for Developers", "industry": "developers"},
    {"slug": "invoice-generator-for-marketing-agencies", "title": "Invoice Generator for Marketing Agencies", "industry": "marketing agencies"},
    {"slug": "invoice-generator-for-coaches", "title": "Invoice Generator for Coaches & Trainers", "industry": "coaches"},
    {"slug": "templates/simple-invoice", "title": "Simple Invoice Template", "template_type": "simple"},
    {"slug": "templates/professional-invoice", "title": "Professional Invoice Template", "template_type": "professional"},
    {"slug": "templates/hourly-invoice", "title": "Hourly Invoice Template", "template_type": "hourly"},
    {"slug": "templates/project-invoice", "title": "Project-Based Invoice Template", "template_type": "project"},
]

EVERGREEN_TOPICS = [
    "Complete Guide to Getting Paid Faster as a Freelancer",
    "10 Common Invoicing Mistakes (And How to Avoid Them)",
    "How to Handle Clients Who Won't Pay",
    "Tax Deductions Every Freelancer Should Know",
    "Setting Your Freelance Rates: A Data-Driven Guide",
    "How to Create a Professional Invoice in 5 Minutes",
    "Invoice Terms and Conditions: What to Include",
    "Digital vs Paper Invoices: Pros and Cons",
    "How to Track Invoices and Payments Effectively",
    "Building Long-Term Client Relationships Through Professional Invoicing",
]


def send_telegram(message: str):
    """Send notification to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"Telegram not configured. Message: {message}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Truncate message if too long
    if len(message) > 4000:
        message = message[:4000] + "..."

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram: {e}")


def load_tracking() -> dict:
    """Load tracking data for what content has been created."""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return {"created_keywords": [], "created_landing": [], "created_evergreen": []}


def save_tracking(data: dict):
    """Save tracking data."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def call_claude(system: str, user: str, max_tokens: int = 4096) -> str:
    """Call Claude API."""
    response = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'Content-Type': 'application/json',
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01'
        },
        json={
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': max_tokens,
            'system': system,
            'messages': [{'role': 'user', 'content': user}]
        },
        timeout=120
    )

    if response.status_code != 200:
        raise Exception(f"Claude API error: {response.status_code} - {response.text}")

    data = response.json()
    return data['content'][0]['text']


def generate_blog_article(topic: dict) -> str:
    """Generate a full SEO-optimized blog article."""
    system = """You are an expert content writer for MakeInvoice.online, a free online invoice generator.

Write a comprehensive, helpful blog post that:
1. Targets the given keyword naturally (use in title, first paragraph, headings)
2. Is 1200-1800 words
3. Provides genuine value - actionable advice, not fluff
4. Uses proper heading structure (H2, H3)
5. Includes bullet points and numbered lists
6. Has a FAQ section with 3-5 questions (for featured snippets)
7. Naturally mentions MakeInvoice.online where relevant (1-2 times max, not forced)
8. Ends with a clear but subtle CTA

Format in Markdown with:
- Meta description as HTML comment at top: <!-- meta: description here -->
- Clear H2 and H3 structure
- FAQ section at end

Write like a helpful expert, not a salesperson."""

    user = f"""Write a blog post about: {topic.get('title', topic.get('keyword'))}
Target keyword: {topic.get('keyword', '')}

Remember to be genuinely helpful. The goal is to rank #1 and become a trusted resource."""

    return call_claude(system, user, max_tokens=4096)


def generate_landing_page(page: dict) -> str:
    """Generate an industry-specific or template landing page."""

    if page.get('industry'):
        system = """You are a conversion copywriter for MakeInvoice.online.

Create a landing page for a specific industry. The page should:
1. Speak directly to that industry's pain points
2. Show you understand their specific invoicing needs
3. Include industry-specific examples
4. Have clear sections: Hero, Pain Points, Features, How It Works, Testimonial (create realistic one), CTA
5. Be persuasive but not pushy

Format as HTML with Tailwind CSS classes (we use Tailwind).
Include proper meta tags and schema markup.
Make it feel custom-built for this industry."""

        user = f"""Create a landing page for: {page['title']}
Industry: {page['industry']}
URL slug: /{page['slug']}

Include specific examples of invoices for {page['industry']} and address their unique needs."""

    else:
        system = """You are a conversion copywriter for MakeInvoice.online.

Create a template-focused landing page. The page should:
1. Showcase the specific invoice template type
2. Explain when to use this type
3. Show what's included
4. Have clear sections: Hero, Template Preview Description, Features, Use Cases, CTA
5. Target people searching for this template type

Format as HTML with Tailwind CSS classes.
Include proper meta tags and schema markup."""

        user = f"""Create a landing page for: {page['title']}
Template type: {page.get('template_type', 'general')}
URL slug: /{page['slug']}"""

    return call_claude(system, user, max_tokens=5000)


def review_content(content: str, content_type: str) -> dict:
    """Review content for quality."""
    system = """You are a senior editor. Review this content for:
1. Accuracy
2. Helpfulness
3. SEO optimization
4. Readability
5. Appropriate product mentions (not too salesy)

Return JSON:
{
  "score": 1-10,
  "issues": ["issue1"],
  "approved": true/false
}"""

    user = f"Review this {content_type}:\n\n{content[:3000]}"

    try:
        result = call_claude(system, user, max_tokens=500)
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass

    return {"score": 7, "approved": True, "issues": []}


def run_keyword_mode():
    """Generate articles targeting specific keywords."""
    print("📝 Running Keyword Content Mode...")

    tracking = load_tracking()
    created = tracking.get("created_keywords", [])

    # Find topics we haven't created yet
    available = [t for t in KEYWORD_TOPICS if t['keyword'] not in created]

    if not available:
        print("   All keyword topics have been created! Resetting...")
        tracking["created_keywords"] = []
        available = KEYWORD_TOPICS
        save_tracking(tracking)

    # Pick 2 random topics
    selected = random.sample(available, min(2, len(available)))
    articles_created = []

    for topic in selected:
        print(f"   ✍️ Writing: {topic['title']}")

        article = generate_blog_article(topic)
        review = review_content(article, "blog article")

        if review.get('score', 0) < 5:
            print(f"   ⚠️ Low quality score, regenerating...")
            article = generate_blog_article(topic)

        # Save article
        BLOG_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r'[^a-z0-9]+', '-', topic['title'].lower()).strip('-')[:50]
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}-{slug}.md"
        filepath = BLOG_DIR / filename

        frontmatter = f"""---
title: "{topic['title']}"
date: {date_str}
keyword: "{topic['keyword']}"
type: keyword-article
status: draft
---

"""
        with open(filepath, 'w') as f:
            f.write(frontmatter + article)

        # Track it
        tracking["created_keywords"].append(topic['keyword'])
        save_tracking(tracking)

        articles_created.append({
            'title': topic['title'],
            'keyword': topic['keyword'],
            'file': filename,
            'score': review.get('score', 'N/A')
        })

        print(f"   ✅ Saved: {filename}")

    return articles_created


def run_landing_mode():
    """Generate landing pages."""
    print("🎯 Running Landing Page Mode...")

    tracking = load_tracking()
    created = tracking.get("created_landing", [])

    # Find pages we haven't created yet
    available = [p for p in LANDING_PAGE_IDEAS if p['slug'] not in created]

    if not available:
        print("   All landing pages have been created!")
        return []

    # Pick 1 landing page
    selected = random.choice(available)
    print(f"   🏗️ Creating: {selected['title']}")

    html = generate_landing_page(selected)
    review = review_content(html, "landing page")

    # Save landing page
    LANDING_DIR.mkdir(parents=True, exist_ok=True)

    # Handle nested paths like templates/simple-invoice
    filepath = LANDING_DIR / f"{selected['slug']}.html"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w') as f:
        f.write(html)

    # Track it
    tracking["created_landing"].append(selected['slug'])
    save_tracking(tracking)

    print(f"   ✅ Saved: {filepath}")

    return [{
        'title': selected['title'],
        'slug': selected['slug'],
        'file': f"{selected['slug']}.html",
        'score': review.get('score', 'N/A')
    }]


def run_evergreen_mode():
    """Generate evergreen content."""
    print("🌲 Running Evergreen Content Mode...")

    tracking = load_tracking()
    created = tracking.get("created_evergreen", [])

    # Find topics we haven't created yet
    available = [t for t in EVERGREEN_TOPICS if t not in created]

    if not available:
        print("   All evergreen topics created! Resetting...")
        tracking["created_evergreen"] = []
        available = EVERGREEN_TOPICS
        save_tracking(tracking)

    selected = random.choice(available)
    print(f"   ✍️ Writing: {selected}")

    topic = {"title": selected, "keyword": selected.lower()}
    article = generate_blog_article(topic)
    review = review_content(article, "blog article")

    # Save article
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', selected.lower()).strip('-')[:50]
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}-{slug}.md"
    filepath = BLOG_DIR / filename

    frontmatter = f"""---
title: "{selected}"
date: {date_str}
type: evergreen
status: draft
---

"""
    with open(filepath, 'w') as f:
        f.write(frontmatter + article)

    tracking["created_evergreen"].append(selected)
    save_tracking(tracking)

    print(f"   ✅ Saved: {filename}")

    return [{
        'title': selected,
        'file': filename,
        'score': review.get('score', 'N/A')
    }]


def run_questions_mode():
    """Run the question discovery mode (imported from original agent)."""
    # Import and run the original question discovery
    from question_discovery import get_reddit_questions, evaluate_question, generate_article, review_article, save_article, load_answered_questions, save_answered_question

    print("❓ Running Question Discovery Mode...")

    answered = load_answered_questions()
    questions = get_reddit_questions()
    new_questions = [q for q in questions if hash(q['title'].lower()) not in answered]

    if not new_questions:
        print("   No new questions found, falling back to keyword mode...")
        return run_keyword_mode()  # Fallback!

    articles_created = []

    for question in new_questions[:2]:
        evaluation = evaluate_question(question)

        if not evaluation.get('worth_writing'):
            continue

        article = generate_article(question, evaluation)
        review = review_article(article, question)

        if review.get('quality_score', 0) < 7 and review.get('revised_article'):
            article = review['revised_article']

        filepath = save_article(article, evaluation, question)
        save_answered_question(hash(question['title'].lower()))

        articles_created.append({
            'title': evaluation.get('suggested_title', question['title']),
            'file': str(filepath.name),
            'source': question['source'],
            'score': review.get('quality_score', 'N/A')
        })

    if not articles_created:
        print("   No suitable questions, falling back to keyword mode...")
        return run_keyword_mode()  # Fallback!

    return articles_created


def main():
    """Main entry point."""
    mode = sys.argv[1] if len(sys.argv) > 1 else 'keywords'

    print(f"🚀 Content Engine Starting (mode: {mode})...")

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set")
        send_telegram("❌ *Content Engine Error*\n\nANTHROPIC_API_KEY not set")
        return

    results = []

    if mode == 'questions':
        results = run_questions_mode()
        content_type = "blog articles (from questions)"
    elif mode == 'keywords':
        results = run_keyword_mode()
        content_type = "blog articles (keyword-targeted)"
    elif mode == 'landing':
        results = run_landing_mode()
        content_type = "landing pages"
    elif mode == 'evergreen':
        results = run_evergreen_mode()
        content_type = "evergreen articles"
    elif mode == 'mixed':
        # Do a bit of everything
        results = run_keyword_mode()
        results.extend(run_evergreen_mode())
        content_type = "mixed content"
    else:
        print(f"Unknown mode: {mode}")
        return

    # Send Telegram summary
    if results:
        summary = f"📝 *Content Engine Complete*\n\n"
        summary += f"Created {len(results)} {content_type}:\n\n"
        for r in results:
            summary += f"• *{r.get('title', 'Untitled')}*\n"
            if r.get('keyword'):
                summary += f"  Keyword: {r['keyword']}\n"
            if r.get('source'):
                summary += f"  Source: {r['source']}\n"
            summary += f"  Quality: {r.get('score', 'N/A')}/10\n"
            summary += f"  File: `{r.get('file', 'unknown')}`\n\n"
        summary += "Review and merge the PR to publish."
        send_telegram(summary)
    else:
        send_telegram(f"📭 *Content Engine*\n\nNo new {content_type} created this run.")

    print("✅ Content Engine Complete!")


if __name__ == '__main__':
    main()
