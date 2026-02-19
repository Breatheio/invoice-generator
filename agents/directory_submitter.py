#!/usr/bin/env python3
"""
Directory Submission Kit Generator

Generates a ready-to-use submission kit for 15 directories.
All descriptions, taglines, keywords and categories are pre-written
by Claude so you can copy-paste directly when submitting.

Output:
  agents/directory_kit.md      - Full submission kit (open this)
  agents/directory_tracking.json - Track submission status

Usage:
  python agents/directory_submitter.py
"""

import os
import json
import re
import requests
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

BASE_DIR = Path(__file__).parent.parent
KIT_FILE = BASE_DIR / 'agents' / 'directory_kit.md'
TRACKING_FILE = BASE_DIR / 'agents' / 'directory_tracking.json'

SITE = {
    "name": "MakeInvoice.online",
    "url": "https://www.makeinvoice.online",
    "email": "support@makeinvoice.online",
    "description": "Free online invoice generator with live preview, PDF download, and customizable templates. No signup required.",
    "features": [
        "100% free to use",
        "No account or signup required",
        "Live preview as you type",
        "Instant PDF download",
        "Customizable templates",
        "Tax calculation built-in",
        "Available in English, German, French, Spanish",
        "Works in any browser",
        "Data stays in your browser — never sent to servers",
    ],
    "target_audience": "Freelancers, small business owners, contractors, consultants, entrepreneurs",
    "category": "Invoicing / Accounting / Business Tools",
    "pricing": "Free (premium plan available)",
}

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

DIRECTORIES = [
    # Tier 1 — High priority, high DA
    {
        "name": "Product Hunt",
        "tier": 1,
        "url": "https://www.producthunt.com",
        "submit_url": "https://www.producthunt.com/posts/new",
        "da": 91,
        "link_type": "dofollow",
        "notes": "Best launched on Tuesday-Thursday. Needs a tagline, description, and thumbnail image. Schedule a launch.",
        "max_tagline": 60,
        "max_description": 260,
    },
    {
        "name": "AlternativeTo",
        "tier": 1,
        "url": "https://alternativeto.net",
        "submit_url": "https://alternativeto.net/software/add/",
        "da": 80,
        "link_type": "dofollow",
        "notes": "Free listing. Add as alternative to FreshBooks, Wave, Invoice Ninja. Very high referral traffic for tools.",
        "max_tagline": 70,
        "max_description": 500,
    },
    {
        "name": "G2",
        "tier": 1,
        "url": "https://www.g2.com",
        "submit_url": "https://sell.g2.com/free-software-listing",
        "da": 87,
        "link_type": "nofollow",
        "notes": "Free listing available. High trust signal for B2B. Requires business email.",
        "max_tagline": 70,
        "max_description": 350,
    },
    {
        "name": "Capterra",
        "tier": 1,
        "url": "https://www.capterra.com",
        "submit_url": "https://www.capterra.com/vendors/sign-up",
        "da": 87,
        "link_type": "nofollow",
        "notes": "Free basic listing. Category: Invoice Management / Billing. High buyer intent traffic.",
        "max_tagline": 70,
        "max_description": 400,
    },
    {
        "name": "GetApp",
        "tier": 1,
        "url": "https://www.getapp.com",
        "submit_url": "https://www.getapp.com/add-a-product/",
        "da": 77,
        "link_type": "nofollow",
        "notes": "Sister site to Capterra. Same company (Gartner). Free listing, worth submitting separately.",
        "max_tagline": 70,
        "max_description": 400,
    },
    # Tier 2 — Good value
    {
        "name": "SaaSHub",
        "tier": 2,
        "url": "https://www.saashub.com",
        "submit_url": "https://www.saashub.com/add-software",
        "da": 65,
        "link_type": "dofollow",
        "notes": "Free listing. Fast approval. Good for indie tools.",
        "max_tagline": 60,
        "max_description": 300,
    },
    {
        "name": "Indie Hackers",
        "tier": 2,
        "url": "https://www.indiehackers.com",
        "submit_url": "https://www.indiehackers.com/products/new",
        "da": 72,
        "link_type": "dofollow",
        "notes": "Create a product page. Great community for bootstrappers. Also post in relevant groups.",
        "max_tagline": 60,
        "max_description": 300,
    },
    {
        "name": "BetaList",
        "tier": 2,
        "url": "https://betalist.com",
        "submit_url": "https://betalist.com/submit",
        "da": 65,
        "link_type": "dofollow",
        "notes": "Free submission. Good for early-stage products. Can take 1-2 weeks for review.",
        "max_tagline": 60,
        "max_description": 250,
    },
    {
        "name": "Uneed",
        "tier": 2,
        "url": "https://www.uneed.best",
        "submit_url": "https://www.uneed.best/submit-a-tool",
        "da": 45,
        "link_type": "dofollow",
        "notes": "Quick submission. Free. Good for tool directories. Fast approval.",
        "max_tagline": 60,
        "max_description": 200,
    },
    {
        "name": "SaaSworthy",
        "tier": 2,
        "url": "https://www.saasworthy.com",
        "submit_url": "https://www.saasworthy.com/add-product",
        "da": 58,
        "link_type": "nofollow",
        "notes": "Free listing. Good for SaaS discovery. Category: Invoice Management.",
        "max_tagline": 70,
        "max_description": 350,
    },
    # Tier 3 — Quick wins
    {
        "name": "Software Advice",
        "tier": 3,
        "url": "https://www.softwareadvice.com",
        "submit_url": "https://www.softwareadvice.com/app/signup",
        "da": 82,
        "link_type": "nofollow",
        "notes": "Gartner-owned (same as Capterra). Free basic listing. Category: Billing & Invoicing.",
        "max_tagline": 70,
        "max_description": 400,
    },
    {
        "name": "Crozdesk",
        "tier": 3,
        "url": "https://crozdesk.com",
        "submit_url": "https://crozdesk.com/software/add",
        "da": 55,
        "link_type": "dofollow",
        "notes": "Free listing. Good for B2B software discovery.",
        "max_tagline": 60,
        "max_description": 300,
    },
    {
        "name": "SourceForge",
        "tier": 3,
        "url": "https://sourceforge.net",
        "submit_url": "https://sourceforge.net/software/add/",
        "da": 93,
        "link_type": "nofollow",
        "notes": "Very high DA. Free listing. Category: Billing/Invoicing. Old but still high traffic.",
        "max_tagline": 60,
        "max_description": 500,
    },
    {
        "name": "Slant",
        "tier": 3,
        "url": "https://www.slant.co",
        "submit_url": "https://www.slant.co/topics/11323/~best-free-invoice-generators",
        "da": 68,
        "link_type": "dofollow",
        "notes": "Add MakeInvoice.online as an option in the 'Best free invoice generators' topic.",
        "max_tagline": 60,
        "max_description": 200,
    },
    {
        "name": "ToolPilot",
        "tier": 3,
        "url": "https://www.toolpilot.ai",
        "submit_url": "https://www.toolpilot.ai/submit",
        "da": 40,
        "link_type": "dofollow",
        "notes": "AI/web tool directory. Free submission. Fast approval.",
        "max_tagline": 60,
        "max_description": 200,
    },
]


# ---------------------------------------------------------------------------
# Claude content generation
# ---------------------------------------------------------------------------

def generate_content_with_claude() -> dict:
    """Generate all submission content variations using Claude."""

    if not ANTHROPIC_API_KEY:
        print("⚠️  No ANTHROPIC_API_KEY — using placeholder content")
        return generate_placeholder_content()

    features_text = "\n".join(f"- {f}" for f in SITE["features"])

    prompt = f"""You are an expert at writing software directory submissions that get approved and drive traffic.

Generate submission content for this product:

Product: {SITE['name']}
URL: {SITE['url']}
What it does: {SITE['description']}
Target audience: {SITE['target_audience']}
Category: {SITE['category']}
Pricing: {SITE['pricing']}
Key features:
{features_text}

Generate the following content variations. Be specific, benefit-focused, and avoid generic marketing speak.

Return ONLY valid JSON in this exact format:
{{
  "tagline": "One-line value proposition, max 60 chars",
  "short": "150 char description highlighting the key benefit",
  "medium": "300 char description covering what it is, who it's for, and key features",
  "long": "500 char description for detailed listings — full pitch covering features, benefits, and target users",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6", "keyword7", "keyword8"],
  "categories": {{
    "primary": "Main category (e.g. Invoicing Software)",
    "secondary": "Secondary category (e.g. Accounting Tools)",
    "tags": ["freelance", "invoicing", "small business", "pdf", "free tool"]
  }},
  "alternatives_to": ["FreshBooks", "Wave", "Invoice Ninja", "Zoho Invoice", "PayPal Invoicing"],
  "one_liner": "Tweet-length description under 120 chars"
}}"""

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
            text = resp.json()["content"][0]["text"].strip()
            json_m = re.search(r'\{.*\}', text, re.DOTALL)
            if json_m:
                return json.loads(json_m.group())
    except Exception as e:
        print(f"Claude error: {e}")

    return generate_placeholder_content()


def generate_placeholder_content() -> dict:
    return {
        "tagline": "Free invoice generator — no signup needed",
        "short": "Create professional invoices instantly. Free, no account required. Live preview + PDF download in seconds.",
        "medium": "MakeInvoice.online is a free invoice generator for freelancers and small businesses. Create professional invoices with live preview, download as PDF instantly. No signup required — works in any browser.",
        "long": "MakeInvoice.online is the easiest way to create professional invoices online. Built for freelancers, contractors, and small business owners who need to invoice clients quickly without expensive software. 100% free, no account needed, instant PDF download. Features include live preview, tax calculation, customizable templates, and support for multiple currencies and languages.",
        "keywords": ["free invoice generator", "invoice maker", "online invoicing", "pdf invoice", "freelance invoice", "small business invoicing", "invoice template", "create invoice online"],
        "categories": {
            "primary": "Invoicing Software",
            "secondary": "Accounting Tools",
            "tags": ["freelance", "invoicing", "small business", "pdf", "free tool", "billing"],
        },
        "alternatives_to": ["FreshBooks", "Wave", "Invoice Ninja", "Zoho Invoice", "PayPal Invoicing"],
        "one_liner": "Free invoice generator — create & download PDF invoices instantly, no signup required.",
    }


# ---------------------------------------------------------------------------
# Markdown kit generator
# ---------------------------------------------------------------------------

def build_markdown_kit(content: dict) -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    tier1 = [d for d in DIRECTORIES if d["tier"] == 1]
    tier2 = [d for d in DIRECTORIES if d["tier"] == 2]
    tier3 = [d for d in DIRECTORIES if d["tier"] == 3]

    keywords_str = ", ".join(content["keywords"])
    tags_str = ", ".join(content["categories"]["tags"])
    alternatives_str = ", ".join(content["alternatives_to"])

    lines = [
        f"# MakeInvoice.online — Directory Submission Kit",
        f"Generated: {date_str}  ",
        f"Email to use: `support@makeinvoice.online`  ",
        f"URL: `https://www.makeinvoice.online`",
        "",
        "---",
        "",
        "## Ready-to-Use Content",
        "",
        "Copy-paste these into any directory form.",
        "",
        f"### Tagline (60 chars)",
        f"```",
        content["tagline"],
        f"```",
        "",
        f"### One-liner (120 chars)",
        f"```",
        content["one_liner"],
        f"```",
        "",
        f"### Short Description (150 chars)",
        f"```",
        content["short"],
        f"```",
        "",
        f"### Medium Description (300 chars)",
        f"```",
        content["medium"],
        f"```",
        "",
        f"### Long Description (500 chars)",
        f"```",
        content["long"],
        f"```",
        "",
        f"### Keywords / Tags",
        f"```",
        keywords_str,
        f"```",
        "",
        f"### Categories",
        f"- **Primary:** {content['categories']['primary']}",
        f"- **Secondary:** {content['categories']['secondary']}",
        f"- **Tags:** {tags_str}",
        "",
        f"### Alternatives To (use when asked)",
        f"```",
        alternatives_str,
        f"```",
        "",
        "---",
        "",
        "## Submission Checklist",
        "",
        "Check off each directory as you submit.",
        "",
    ]

    for tier_num, tier_dirs, tier_label in [
        (1, tier1, "🔴 Tier 1 — High Priority (do these first)"),
        (2, tier2, "🟡 Tier 2 — Good Value"),
        (3, tier3, "🟢 Tier 3 — Quick Wins"),
    ]:
        lines.append(f"### {tier_label}")
        lines.append("")
        for d in tier_dirs:
            lines.append(f"#### {d['name']}")
            lines.append(f"- [ ] **Status:** Not submitted")
            lines.append(f"- **Submit here:** [{d['submit_url']}]({d['submit_url']})")
            lines.append(f"- **DA:** {d['da']} | **Link:** {d['link_type']}")
            lines.append(f"- **Note:** {d['notes']}")
            lines.append("")

    lines += [
        "---",
        "",
        "## Assets Checklist",
        "",
        "Have these ready before submitting:",
        "",
        "- [ ] Screenshot of the invoice generator (1280x800px)",
        "- [ ] Logo PNG (512x512px, transparent background)",
        "- [ ] Logo PNG (192x192px, for smaller fields)",
        "- [ ] OG image / banner (1200x630px)",
        "",
        "---",
        "",
        "## Tips",
        "",
        "- **ProductHunt:** Launch on Tuesday-Thursday for max exposure. Engage with comments on launch day.",
        "- **AlternativeTo:** Add as alternative to FreshBooks, Wave, Invoice Ninja — this drives traffic from people searching for free alternatives.",
        "- **G2/Capterra:** Ask your first users to leave a review — even 2-3 reviews boosts visibility significantly.",
        "- **Indie Hackers:** Post a 'Show IH' post about building MakeInvoice, link to the product page.",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

def load_tracking() -> dict:
    if TRACKING_FILE.exists():
        return json.loads(TRACKING_FILE.read_text())
    return {"submissions": {}}


def save_tracking(tracking: dict):
    TRACKING_FILE.write_text(json.dumps(tracking, indent=2))


def init_tracking():
    tracking = load_tracking()
    for d in DIRECTORIES:
        if d["name"] not in tracking["submissions"]:
            tracking["submissions"][d["name"]] = {
                "status": "pending",
                "submitted_date": None,
                "approved_date": None,
                "backlink_url": None,
                "notes": "",
            }
    save_tracking(tracking)
    return tracking


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("📋 Directory Submission Kit Generator\n")

    print("🤖 Generating optimized content with Claude...")
    content = generate_content_with_claude()
    print("✅ Content generated\n")

    print("📝 Building submission kit...")
    kit_markdown = build_markdown_kit(content)
    KIT_FILE.write_text(kit_markdown, encoding='utf-8')
    print(f"✅ Kit saved to: {KIT_FILE}")

    print("📊 Initializing tracking file...")
    init_tracking()
    print(f"✅ Tracking saved to: {TRACKING_FILE}\n")

    print("=" * 50)
    print(f"✅ Done! Open this file to start submitting:")
    print(f"   agents/directory_kit.md")
    print("=" * 50)
    print(f"\nTagline generated: \"{content['tagline']}\"")
    print(f"\n{len(DIRECTORIES)} directories ready:")
    for d in DIRECTORIES:
        tier_icon = {1: "🔴", 2: "🟡", 3: "🟢"}[d["tier"]]
        print(f"  {tier_icon} {d['name']} (DA {d['da']}, {d['link_type']})")


if __name__ == "__main__":
    main()
