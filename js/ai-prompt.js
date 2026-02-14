// AI Invoice Prompt Feature
// Handles the AI-powered natural language invoice generation

const AI_STORAGE_KEY = 'invoiceApp_aiUsage';
const FREE_DAILY_LIMIT = 3;

const AIPrompt = {
  // Get current usage data
  getUsage() {
    try {
      const stored = localStorage.getItem(AI_STORAGE_KEY);
      if (!stored) return { date: null, count: 0 };
      return JSON.parse(stored);
    } catch (e) {
      return { date: null, count: 0 };
    }
  },

  // Set usage data
  setUsage(data) {
    try {
      localStorage.setItem(AI_STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      console.error('Failed to save AI usage:', e);
    }
  },

  // Get today's date string (YYYY-MM-DD)
  getTodayString() {
    return new Date().toISOString().split('T')[0];
  },

  // Check remaining prompts for free users
  getRemainingPrompts() {
    const usage = this.getUsage();
    const today = this.getTodayString();

    // Reset count if it's a new day
    if (usage.date !== today) {
      return FREE_DAILY_LIMIT;
    }

    return Math.max(0, FREE_DAILY_LIMIT - usage.count);
  },

  // Increment usage count
  incrementUsage() {
    const usage = this.getUsage();
    const today = this.getTodayString();

    // Reset if new day
    if (usage.date !== today) {
      this.setUsage({ date: today, count: 1 });
    } else {
      this.setUsage({ date: today, count: usage.count + 1 });
    }
  },

  // Check if user can use AI prompt
  canUsePrompt(isPremium) {
    if (isPremium) return true;
    return this.getRemainingPrompts() > 0;
  },

  // Call the AI API
  async parseInvoice(prompt) {
    const response = await fetch('/api/parse-invoice', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to parse invoice');
    }

    return data;
  },
};

// Export for use in app.js
window.AIPrompt = AIPrompt;
