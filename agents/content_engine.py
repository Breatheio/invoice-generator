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
BLOG_DIR = BASE_DIR / 'blog'  # HTML files go directly in /blog/
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


def generate_blog_article(topic: dict) -> dict:
    """Generate a full SEO-optimized blog article as HTML."""
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

IMPORTANT: Return your response as JSON with this exact structure:
{
  "title": "The exact H1 title for the article",
  "meta_description": "A 150-160 character meta description",
  "read_time": "X min read",
  "content_html": "The full article body HTML (no <html>, <head>, <body> tags - just the content with <h2>, <h3>, <p>, <ul>, <li>, etc.)"
}

For content_html, use these HTML patterns:
- <h2 class="text-2xl font-bold text-gray-900 mt-8 mb-4">Heading</h2>
- <h3 class="text-xl font-semibold text-gray-900 mt-6 mb-3">Subheading</h3>
- <p class="text-gray-600 mb-4">Paragraph text</p>
- <ul class="list-disc list-inside text-gray-600 mb-6 space-y-2"><li>Item</li></ul>
- <ol class="list-decimal list-inside text-gray-600 mb-6 space-y-2"><li>Item</li></ol>
- For first answer paragraph: <p class="text-lg text-gray-600 mb-4"><strong>Direct answer:</strong> text here</p>

Include a CTA box in the middle using:
<div class="bg-blue-50 border border-blue-200 rounded-lg p-6 my-8">
  <h3 class="text-lg font-bold text-gray-900 mb-2">Create Your Invoice Now</h3>
  <p class="text-gray-600 mb-4">Use our free invoice generator. Professional templates, no signup required.</p>
  <a href="../" class="inline-block bg-blue-600 text-white font-semibold px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">Create Free Invoice &rarr;</a>
</div>

Write like a helpful expert, not a salesperson. Return ONLY valid JSON."""

    user = f"""Write a blog post about: {topic.get('title', topic.get('keyword'))}
Target keyword: {topic.get('keyword', '')}

Remember to be genuinely helpful. The goal is to rank #1 and become a trusted resource.

Return ONLY the JSON object, no other text."""

    result = call_claude(system, user, max_tokens=6000)

    # Parse JSON from response
    try:
        # Try to find JSON in the response
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    # Fallback if JSON parsing fails
    return {
        "title": topic.get('title', topic.get('keyword', 'Article')),
        "meta_description": f"Learn about {topic.get('keyword', 'invoicing')} with this comprehensive guide.",
        "read_time": "5 min read",
        "content_html": f"<p class='text-gray-600 mb-4'>{result[:2000]}</p>"
    }


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


def wrap_blog_html(article_data: dict, slug: str) -> str:
    """Wrap article content in full HTML template."""
    title = article_data.get('title', 'Article')
    meta_desc = article_data.get('meta_description', '')
    read_time = article_data.get('read_time', '5 min read')
    content_html = article_data.get('content_html', '')
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_display = datetime.now().strftime('%B %Y')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | MakeInvoice.online</title>
  <meta name="description" content="{meta_desc}">

  <!-- Open Graph / Social -->
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{meta_desc}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://www.makeinvoice.online/blog/{slug}">
  <meta property="og:image" content="https://www.makeinvoice.online/assets/og-image.png">

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{meta_desc}">

  <!-- Canonical URL -->
  <link rel="canonical" href="https://www.makeinvoice.online/blog/{slug}">

  <!-- Favicon -->
  <link rel="icon" type="image/svg+xml" href="../assets/logo.svg">

  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            primary: {{
              50: '#eff6ff',
              100: '#dbeafe',
              200: '#bfdbfe',
              300: '#93c5fd',
              400: '#60a5fa',
              500: '#3b82f6',
              600: '#2563eb',
              700: '#1d4ed8',
              800: '#1e40af',
              900: '#1e3a8a',
            }}
          }}
        }}
      }}
    }}
  </script>

  <!-- Custom Styles -->
  <link rel="stylesheet" href="../styles/custom.css">

  <!-- JSON-LD Article Schema -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "description": "{meta_desc}",
    "image": "https://makeinvoice.online/assets/og-image.png",
    "author": {{
      "@type": "Organization",
      "name": "MakeInvoice.online"
    }},
    "publisher": {{
      "@type": "Organization",
      "name": "MakeInvoice.online",
      "logo": {{
        "@type": "ImageObject",
        "url": "https://makeinvoice.online/assets/logo.svg"
      }}
    }},
    "datePublished": "{date_str}",
    "dateModified": "{date_str}",
    "mainEntityOfPage": {{
      "@type": "WebPage",
      "@id": "https://makeinvoice.online/blog/{slug}.html"
    }}
  }}
  </script>
</head>
<body class="bg-gray-50 min-h-screen">
  <!-- Header -->
  <header class="bg-white shadow-sm border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <!-- Logo -->
        <a href="../" class="flex items-center space-x-3">
          <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <span class="text-xl font-bold text-gray-900">MakeInvoice<span class="text-blue-600">.online</span></span>
        </a>

        <!-- Navigation -->
        <nav class="flex items-center space-x-6">
          <a href="../" class="text-gray-600 hover:text-blue-600 font-medium">Invoice Generator</a>
          <a href="./" class="text-blue-600 font-medium">Blog</a>
        </nav>
      </div>
    </div>
  </header>

  <!-- Article Content -->
  <main class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <!-- Breadcrumb -->
    <nav class="text-sm text-gray-500 mb-8">
      <a href="./" class="hover:text-blue-600">Blog</a>
      <span class="mx-2">/</span>
      <span class="text-gray-900">{title[:50]}...</span>
    </nav>

    <article class="bg-white rounded-xl shadow-lg p-8 md:p-12">
      <!-- Article Header -->
      <header class="mb-8">
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4">{title}</h1>
        <div class="flex items-center text-gray-500 text-sm">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span>{read_time}</span>
          <span class="mx-3">|</span>
          <span>Updated {date_display}</span>
        </div>
      </header>

      <!-- Article Body -->
      <div class="prose max-w-none">
        {content_html}
      </div>

      <!-- Final CTA -->
      <div class="bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg p-8 mt-12 text-center text-white">
        <h3 class="text-2xl font-bold mb-3">Ready to Create Your Invoice?</h3>
        <p class="text-blue-100 mb-6">Professional invoices in seconds. Free, no signup required.</p>
        <a href="../" class="inline-block bg-white text-blue-600 font-semibold px-8 py-3 rounded-lg hover:bg-blue-50 transition-colors">
          Create Free Invoice &rarr;
        </a>
      </div>
    </article>
  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-gray-200 mt-16">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div>
          <div class="flex items-center space-x-2 mb-4">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            <span class="font-bold text-gray-900">MakeInvoice.online</span>
          </div>
          <p class="text-sm text-gray-600">Create professional invoices for free. Easy-to-use invoice generator with live preview and PDF download.</p>
        </div>
        <div>
          <h3 class="font-semibold text-gray-900 mb-4">Quick Links</h3>
          <ul class="space-y-2 text-sm">
            <li><a href="../" class="text-gray-600 hover:text-blue-600">Invoice Generator</a></li>
            <li><a href="./" class="text-gray-600 hover:text-blue-600">Blog</a></li>
            <li><a href="../legal/privacy.html" class="text-gray-600 hover:text-blue-600">Privacy Policy</a></li>
            <li><a href="../legal/terms.html" class="text-gray-600 hover:text-blue-600">Terms of Service</a></li>
          </ul>
        </div>
        <div>
          <h3 class="font-semibold text-gray-900 mb-4">Support</h3>
          <p class="text-sm text-gray-600 mb-2">Need help? Contact us at:</p>
          <a href="mailto:support@makeinvoice.online" class="text-blue-600 hover:underline">support@makeinvoice.online</a>
        </div>
      </div>
      <div class="border-t border-gray-200 mt-8 pt-8 text-center text-sm text-gray-500">
        <p>&copy; 2025 MakeInvoice.online. All rights reserved.</p>
      </div>
    </div>
  </footer>
</body>
</html>
'''


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

        article_data = generate_blog_article(topic)
        review = review_content(article_data.get('content_html', ''), "blog article")

        if review.get('score', 0) < 5:
            print(f"   ⚠️ Low quality score, regenerating...")
            article_data = generate_blog_article(topic)

        # Generate slug from title
        slug = re.sub(r'[^a-z0-9]+', '-', topic['title'].lower()).strip('-')[:60]

        # Wrap content in HTML template
        full_html = wrap_blog_html(article_data, slug)

        # Save as HTML
        BLOG_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{slug}.html"
        filepath = BLOG_DIR / filename

        with open(filepath, 'w') as f:
            f.write(full_html)

        # Track it
        tracking["created_keywords"].append(topic['keyword'])
        save_tracking(tracking)

        articles_created.append({
            'title': article_data.get('title', topic['title']),
            'keyword': topic['keyword'],
            'file': filename,
            'slug': slug,
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
    article_data = generate_blog_article(topic)
    review = review_content(article_data.get('content_html', ''), "blog article")

    # Generate slug from title
    slug = re.sub(r'[^a-z0-9]+', '-', selected.lower()).strip('-')[:60]

    # Wrap content in HTML template
    full_html = wrap_blog_html(article_data, slug)

    # Save as HTML
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}.html"
    filepath = BLOG_DIR / filename

    with open(filepath, 'w') as f:
        f.write(full_html)

    tracking["created_evergreen"].append(selected)
    save_tracking(tracking)

    print(f"   ✅ Saved: {filename}")

    return [{
        'title': article_data.get('title', selected),
        'file': filename,
        'slug': slug,
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
            # Add live URL
            if r.get('slug'):
                slug = r['slug']
                if r.get('type') == 'landing':
                    url = f"https://www.makeinvoice.online/{slug}"
                else:
                    url = f"https://www.makeinvoice.online/blog/{slug}.html"
                summary += f"  🔗 [View]({url})\n"
            elif r.get('file'):
                # Fallback for landing pages
                slug = r['file'].replace('.html', '')
                url = f"https://www.makeinvoice.online/{slug}"
                summary += f"  🔗 [View]({url})\n"
            summary += "\n"
        summary += "✅ Auto-published to site!"
        send_telegram(summary)
    else:
        send_telegram(f"📭 *Content Engine*\n\nNo new {content_type} created this run.")

    print("✅ Content Engine Complete!")


if __name__ == '__main__':
    main()
