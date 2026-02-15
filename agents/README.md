# SEO Automation Agents

Automated agents for continuous SEO/AEO optimization.

## Question Discovery Agent

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
