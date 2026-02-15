#!/usr/bin/env python3
"""
Question Discovery Agent
Finds questions people ask about invoicing, generates SEO-optimized articles,
reviews them for quality, and notifies via Telegram.

Run weekly via GitHub Actions.
"""

import os
import json
import re
import requests
from datetime import datetime
from pathlib import Path

# Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID', '')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET', '')

# Subreddits to monitor
SUBREDDITS = ['freelance', 'smallbusiness', 'Entrepreneur', 'accounting', 'selfemployed']

# Keywords to search
KEYWORDS = ['invoice', 'invoicing', 'billing client', 'payment terms', 'charge client']

# Path to track answered questions
ANSWERED_FILE = Path(__file__).parent.parent / 'blog' / '.answered_questions.json'
BLOG_DIR = Path(__file__).parent.parent / 'blog' / 'posts'


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


def get_reddit_questions() -> list:
    """Fetch recent questions from Reddit about invoicing."""
    questions = []

    headers = {'User-Agent': 'InvoiceBot/1.0'}

    # If we have Reddit API credentials, use them
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
        token_response = requests.post(
            'https://www.reddit.com/api/v1/access_token',
            auth=auth,
            data={'grant_type': 'client_credentials'},
            headers=headers,
            timeout=10
        )
        if token_response.status_code == 200:
            token = token_response.json().get('access_token')
            headers['Authorization'] = f'Bearer {token}'

    for subreddit in SUBREDDITS:
        for keyword in KEYWORDS:
            try:
                # Search Reddit
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    'q': keyword,
                    'sort': 'new',
                    'limit': 10,
                    't': 'month',
                    'restrict_sr': 'true'
                }
                response = requests.get(url, headers=headers, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    for post in data.get('data', {}).get('children', []):
                        post_data = post.get('data', {})
                        title = post_data.get('title', '')
                        selftext = post_data.get('selftext', '')[:500]
                        score = post_data.get('score', 0)
                        num_comments = post_data.get('num_comments', 0)
                        url = f"https://reddit.com{post_data.get('permalink', '')}"

                        # Filter for questions (has ? or starts with question words)
                        if '?' in title or any(title.lower().startswith(w) for w in ['how', 'what', 'why', 'when', 'should', 'can', 'do', 'is']):
                            questions.append({
                                'source': f'r/{subreddit}',
                                'title': title,
                                'body': selftext,
                                'score': score,
                                'comments': num_comments,
                                'url': url,
                                'engagement': score + num_comments * 2
                            })
            except Exception as e:
                print(f"Error fetching from r/{subreddit}: {e}")

    # Sort by engagement and dedupe
    seen_titles = set()
    unique_questions = []
    for q in sorted(questions, key=lambda x: x['engagement'], reverse=True):
        title_lower = q['title'].lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_questions.append(q)

    return unique_questions[:20]  # Top 20


def load_answered_questions() -> set:
    """Load set of questions we've already answered."""
    if ANSWERED_FILE.exists():
        with open(ANSWERED_FILE, 'r') as f:
            return set(json.load(f))
    return set()


def save_answered_question(question_hash: str):
    """Mark a question as answered."""
    answered = load_answered_questions()
    answered.add(question_hash)
    ANSWERED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ANSWERED_FILE, 'w') as f:
        json.dump(list(answered), f)


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


def evaluate_question(question: dict) -> dict:
    """Use Claude to evaluate if a question is worth writing about."""
    system = """You are an SEO content strategist for MakeInvoice.online, a free invoice generator.
Evaluate if this question is worth writing a blog post about.

Consider:
- Search potential (would people Google this?)
- Relevance to our product (invoice generator)
- Ability to naturally mention our tool
- Competition (is this already well-answered online?)

Return JSON only:
{
  "worth_writing": true/false,
  "reason": "brief explanation",
  "search_potential": "high/medium/low",
  "suggested_title": "SEO-optimized title",
  "target_keywords": ["keyword1", "keyword2"]
}"""

    user = f"""Question from {question['source']}:
Title: {question['title']}
Body: {question['body']}
Engagement: {question['engagement']} (score + comments)"""

    try:
        result = call_claude(system, user, max_tokens=500)
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Error evaluating question: {e}")

    return {'worth_writing': False, 'reason': 'Evaluation failed'}


def generate_article(question: dict, evaluation: dict) -> str:
    """Generate a full SEO-optimized blog article."""
    system = """You are an expert content writer for MakeInvoice.online, a free online invoice generator.

Write a comprehensive, helpful blog post that:
1. Directly answers the user's question
2. Is SEO-optimized for the target keywords
3. Includes practical, actionable advice
4. Naturally mentions MakeInvoice.online where relevant (not forced)
5. Uses proper heading structure (H2, H3)
6. Includes a FAQ section at the end with 3-4 related questions
7. Is 1000-1500 words

Format the article in Markdown with:
- Engaging title (H1)
- Meta description (in a comment at top)
- Clear sections with H2 headings
- Bullet points and numbered lists where appropriate
- FAQ section at the end
- Brief author bio mentioning MakeInvoice.online

Do NOT include generic fluff. Every sentence should add value."""

    user = f"""Write an article based on this question:

Original Question: {question['title']}
Context: {question['body']}
Source: {question['source']}

Target Keywords: {', '.join(evaluation.get('target_keywords', []))}
Suggested Title: {evaluation.get('suggested_title', question['title'])}

Remember: Be genuinely helpful first. The goal is to become a trusted resource, not to hard-sell our product."""

    return call_claude(system, user, max_tokens=4096)


def review_article(article: str, question: dict) -> dict:
    """Have Claude review the article for quality."""
    system = """You are a senior editor reviewing a blog post for MakeInvoice.online.

Review the article for:
1. Accuracy - Is the information correct?
2. Helpfulness - Does it actually answer the question?
3. SEO - Good title, headings, keyword usage?
4. Readability - Clear, engaging, well-structured?
5. CTA - Natural mention of the product (not too salesy)?
6. Completeness - Are there gaps?

Return JSON:
{
  "approved": true/false,
  "quality_score": 1-10,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "revised_article": "full revised article if score < 7, otherwise null"
}"""

    user = f"""Original question: {question['title']}

Article to review:
{article}"""

    try:
        result = call_claude(system, user, max_tokens=5000)
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Error reviewing article: {e}")

    return {'approved': False, 'quality_score': 0, 'issues': ['Review failed']}


def save_article(article: str, evaluation: dict, question: dict) -> Path:
    """Save article to blog directory."""
    BLOG_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename from title
    title = evaluation.get('suggested_title', question['title'])
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:50]
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}-{slug}.md"

    filepath = BLOG_DIR / filename

    # Add frontmatter
    frontmatter = f"""---
title: "{title}"
date: {date_str}
keywords: {json.dumps(evaluation.get('target_keywords', []))}
source: "{question['source']}"
source_url: "{question.get('url', '')}"
status: draft
---

"""

    with open(filepath, 'w') as f:
        f.write(frontmatter + article)

    return filepath


def main():
    """Main agent workflow."""
    print("🔍 Question Discovery Agent Starting...")

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    # Load already answered questions
    answered = load_answered_questions()

    # Fetch questions from Reddit
    print("📥 Fetching questions from Reddit...")
    questions = get_reddit_questions()
    print(f"   Found {len(questions)} potential questions")

    # Filter out already answered
    new_questions = [q for q in questions if hash(q['title'].lower()) not in answered]
    print(f"   {len(new_questions)} new questions after filtering")

    if not new_questions:
        send_telegram("📭 *Question Discovery Agent*\n\nNo new questions found this week.")
        return

    articles_created = []

    # Process top 3 questions
    for question in new_questions[:3]:
        print(f"\n📝 Evaluating: {question['title'][:60]}...")

        # Evaluate if worth writing about
        evaluation = evaluate_question(question)

        if not evaluation.get('worth_writing'):
            print(f"   ❌ Skipping: {evaluation.get('reason')}")
            continue

        print(f"   ✅ Worth writing! Search potential: {evaluation.get('search_potential')}")

        # Generate article
        print("   ✍️ Generating article...")
        article = generate_article(question, evaluation)

        # Review article
        print("   🔍 Reviewing article...")
        review = review_article(article, question)

        if review.get('quality_score', 0) < 7 and review.get('revised_article'):
            print(f"   📝 Quality score {review['quality_score']}/10 - using revised version")
            article = review['revised_article']

        # Save article
        filepath = save_article(article, evaluation, question)
        print(f"   💾 Saved to {filepath}")

        # Mark as answered
        save_answered_question(hash(question['title'].lower()))

        articles_created.append({
            'title': evaluation.get('suggested_title', question['title']),
            'file': str(filepath.name),
            'source': question['source'],
            'quality': review.get('quality_score', 'N/A')
        })

    # Send summary to Telegram
    if articles_created:
        summary = "📝 *Question Discovery Agent*\n\n"
        summary += f"Created {len(articles_created)} article(s):\n\n"
        for a in articles_created:
            summary += f"• *{a['title']}*\n"
            summary += f"  Source: {a['source']} | Quality: {a['quality']}/10\n"
            summary += f"  File: `{a['file']}`\n\n"
        summary += "Review and approve the PR to publish."
        send_telegram(summary)
    else:
        send_telegram("📭 *Question Discovery Agent*\n\nEvaluated questions but none were worth writing about this week.")

    print("\n✅ Agent completed!")


if __name__ == '__main__':
    main()
