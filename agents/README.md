# SEO Automation Agents

Automated agents for continuous SEO/AEO optimization.

## Content Schedule

| Day | Mode | What it creates |
|-----|------|-----------------|
| **Monday** | `questions` | Blog articles from Reddit/Quora questions |
| **Wednesday** | `keywords` | SEO articles targeting specific keywords |
| **Friday** | `landing` | Industry/template landing pages |

## Content Engine

The unified content generation system. Runs automatically 3x per week.

### Modes

- **questions**: Finds Reddit/Quora questions → generates answer articles
- **keywords**: Targets specific SEO keywords (15+ pre-defined topics)
- **landing**: Creates industry-specific landing pages (14 industries)
- **evergreen**: Creates timeless how-to content
- **mixed**: Combination of keywords + evergreen

### Fallback Logic

If `questions` mode finds no new questions, it automatically falls back to `keywords` mode so you always get content.

### Manual Run

Go to Actions → Content Engine → Run workflow → Select mode

---

## Question Discovery Agent (Legacy)

Runs weekly to find questions people ask about invoicing and generate blog articles.

### What it does

1. **Discovers questions** from Reddit (r/freelance, r/smallbusiness, etc.)
2. **Evaluates** which questions are worth writing about
3. **Generates** full SEO-optimized blog articles
4. **Reviews** articles for quality (rewrites if needed)
5. **Creates PR** for human approval
6. **Notifies** via Telegram

### Setup

Add these secrets to your GitHub repository (Settings → Secrets → Actions):

| Secret | Required | Description |
|--------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Claude API key |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token (get from @BotFather) |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat ID |
| `REDDIT_CLIENT_ID` | No | Reddit API client ID (optional, improves rate limits) |
| `REDDIT_CLIENT_SECRET` | No | Reddit API client secret |

### Getting Telegram credentials

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token
4. Message your new bot (send any message)
5. Get your chat ID: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
6. Look for `"chat":{"id":123456789}` - that number is your chat ID

### Manual trigger

Go to Actions → Question Discovery Agent → Run workflow

### Schedule

Runs every Monday at 9am UTC. Edit `.github/workflows/question-discovery.yml` to change.

## Workflow

```
┌─────────────────┐
│  Weekly Cron    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch Reddit    │
│ Questions       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Claude Evaluates│
│ Worth writing?  │
└────────┬────────┘
         │ Yes
         ▼
┌─────────────────┐
│ Claude Writes   │
│ Full Article    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Claude Reviews  │
│ Quality Check   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create PR       │
│ Notify Telegram │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Human Reviews   │
│ Merge to Publish│
└─────────────────┘
```
