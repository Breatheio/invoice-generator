// localStorage helper functions
const STORAGE_KEYS = {
  BUSINESS_INFO: 'invoiceApp_businessInfo',
  PREFERENCES: 'invoiceApp_preferences',
  PADDLE_CUSTOMER: 'invoiceApp_paddleCustomer',
  DRAFT: 'invoiceApp_draft',
  HISTORY: 'invoiceApp_history',
};

const MAX_HISTORY_ITEMS = 50; // Limit to prevent localStorage overflow

const Storage = {
  // Generic get/set
  get(key) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (e) {
      console.error('Storage.get error:', e);
      return null;
    }
  },

  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      console.error('Storage.set error:', e);
      return false;
    }
  },

  remove(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (e) {
      console.error('Storage.remove error:', e);
      return false;
    }
  },

  // Business info (premium feature)
  getBusinessInfo() {
    return this.get(STORAGE_KEYS.BUSINESS_INFO) || {
      name: '',
      email: '',
      phone: '',
      address: '',
      logo: null,
    };
  },

  setBusinessInfo(info) {
    return this.set(STORAGE_KEYS.BUSINESS_INFO, info);
  },

  // User preferences
  getPreferences() {
    return this.get(STORAGE_KEYS.PREFERENCES) || {
      currency: 'USD',
      taxRate: 0,
      template: 'classic',
    };
  },

  setPreferences(prefs) {
    return this.set(STORAGE_KEYS.PREFERENCES, prefs);
  },

  // Paddle subscription
  getPaddleCustomer() {
    return this.get(STORAGE_KEYS.PADDLE_CUSTOMER);
  },

  setPaddleCustomer(customer) {
    return this.set(STORAGE_KEYS.PADDLE_CUSTOMER, customer);
  },

  clearPaddleCustomer() {
    return this.remove(STORAGE_KEYS.PADDLE_CUSTOMER);
  },

  // Draft auto-save
  getDraft() {
    return this.get(STORAGE_KEYS.DRAFT);
  },

  setDraft(draft) {
    return this.set(STORAGE_KEYS.DRAFT, {
      ...draft,
      savedAt: new Date().toISOString(),
    });
  },

  clearDraft() {
    return this.remove(STORAGE_KEYS.DRAFT);
  },

  hasDraft() {
    return this.get(STORAGE_KEYS.DRAFT) !== null;
  },

  // Invoice history
  getHistory() {
    return this.get(STORAGE_KEYS.HISTORY) || [];
  },

  addToHistory(invoice) {
    const history = this.getHistory();

    // Create history entry with unique ID and timestamp
    const entry = {
      id: Date.now().toString(),
      savedAt: new Date().toISOString(),
      invoiceNumber: invoice.invoice?.number || 'Unknown',
      clientName: invoice.client?.name || 'Unknown Client',
      total: invoice.total || 0,
      currency: invoice.currency || 'USD',
      data: invoice,
    };

    // Add to beginning of array
    history.unshift(entry);

    // Limit history size
    if (history.length > MAX_HISTORY_ITEMS) {
      history.pop();
    }

    this.set(STORAGE_KEYS.HISTORY, history);
    return entry;
  },

  removeFromHistory(id) {
    const history = this.getHistory();
    const filtered = history.filter(item => item.id !== id);
    this.set(STORAGE_KEYS.HISTORY, filtered);
    return filtered;
  },

  clearHistory() {
    return this.remove(STORAGE_KEYS.HISTORY);
  },

  getHistoryItem(id) {
    const history = this.getHistory();
    return history.find(item => item.id === id);
  },
};

// Premium status check
function isPremium() {
  const paddle = Storage.getPaddleCustomer();
  if (!paddle) return false;
  if (paddle.status !== 'active') return false;
  if (paddle.expiresAt && new Date(paddle.expiresAt) < new Date()) return false;
  return true;
}
