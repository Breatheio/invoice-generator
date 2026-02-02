// localStorage helper functions
const STORAGE_KEYS = {
  BUSINESS_INFO: 'invoiceApp_businessInfo',
  PREFERENCES: 'invoiceApp_preferences',
  PADDLE_CUSTOMER: 'invoiceApp_paddleCustomer',
};

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
};

// Premium status check
function isPremium() {
  const paddle = Storage.getPaddleCustomer();
  if (!paddle) return false;
  if (paddle.status !== 'active') return false;
  if (paddle.expiresAt && new Date(paddle.expiresAt) < new Date()) return false;
  return true;
}
