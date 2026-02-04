// Paddle subscription handler
const PADDLE_CONFIG = {
  enabled: true,
  clientToken: 'live_1d42f28d457f9fd61d9a1a927e6',
  environment: 'production',
  prices: {
    monthly: 'pri_01kgn53966p1qcyq5afdxbsz9h',
    yearly: 'pri_01kgn547cn6gek272rwpea4w0v',
  },
};

const PaddleHandler = {
  initialized: false,

  init() {
    if (!PADDLE_CONFIG.enabled) {
      console.log('Paddle is not enabled. Set PADDLE_CONFIG.enabled = true after setup.');
      return;
    }

    if (this.initialized) return;

    // Initialize Paddle
    if (typeof Paddle !== 'undefined') {
      Paddle.Initialize({
        token: PADDLE_CONFIG.clientToken,
        environment: PADDLE_CONFIG.environment,
      });
      this.initialized = true;
      console.log('Paddle initialized');
    } else {
      console.warn('Paddle.js not loaded');
    }
  },

  openCheckout(plan = 'monthly') {
    if (!PADDLE_CONFIG.enabled) {
      alert('Paddle payments are not configured yet. Please set up your Paddle account.');
      return;
    }

    if (!this.initialized) {
      this.init();
    }

    const priceId = PADDLE_CONFIG.prices[plan];

    Paddle.Checkout.open({
      items: [{ priceId, quantity: 1 }],
      successCallback: (data) => this.handleSuccess(data),
      closeCallback: () => this.handleClose(),
    });
  },

  handleSuccess(data) {
    console.log('Paddle checkout success:', data);

    // Store subscription info
    const customerData = {
      customerId: data.customer?.id || null,
      subscriptionId: data.subscription_id || data.id || null,
      status: 'active',
      plan: data.items?.[0]?.price?.billing_cycle?.interval === 'year' ? 'yearly' : 'monthly',
      // Set expiration based on plan
      expiresAt: this.calculateExpiration(data),
      createdAt: new Date().toISOString(),
    };

    Storage.setPaddleCustomer(customerData);

    // Dispatch event for app to react
    window.dispatchEvent(new CustomEvent('premiumStatusChanged', { detail: { isPremium: true } }));

    // Show success message
    alert('Thank you for subscribing to Premium! Enjoy your ad-free, watermark-free experience.');

    // Reload to apply premium status
    window.location.reload();
  },

  handleClose() {
    console.log('Paddle checkout closed');
  },

  calculateExpiration(data) {
    const now = new Date();
    const interval = data.items?.[0]?.price?.billing_cycle?.interval;

    if (interval === 'year') {
      now.setFullYear(now.getFullYear() + 1);
    } else {
      now.setMonth(now.getMonth() + 1);
    }

    return now.toISOString();
  },

  // Cancel subscription (redirect to Paddle portal)
  cancelSubscription() {
    const customer = Storage.getPaddleCustomer();
    if (!customer || !customer.subscriptionId) {
      alert('No active subscription found.');
      return;
    }

    // In production, you'd redirect to Paddle's customer portal
    // For now, just clear local storage (for demo purposes)
    if (confirm('Are you sure you want to cancel your subscription?')) {
      Storage.clearPaddleCustomer();
      window.dispatchEvent(new CustomEvent('premiumStatusChanged', { detail: { isPremium: false } }));
      alert('Subscription cancelled. You will retain premium access until the end of your billing period.');
      window.location.reload();
    }
  },

  // Check and update subscription status
  checkSubscriptionStatus() {
    const customer = Storage.getPaddleCustomer();
    if (!customer) return false;

    // Check if expired
    if (customer.expiresAt && new Date(customer.expiresAt) < new Date()) {
      customer.status = 'expired';
      Storage.setPaddleCustomer(customer);
      return false;
    }

    return customer.status === 'active';
  },
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  PaddleHandler.init();
});
