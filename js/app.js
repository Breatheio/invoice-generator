// Main Alpine.js application
document.addEventListener('alpine:init', () => {
  Alpine.data('invoiceApp', () => ({
    // App state
    isPremium: false,
    isGeneratingPDF: false,
    showPricingModal: false,
    activeTab: 'form', // 'form' or 'preview' for mobile

    // Business info (your company)
    business: {
      name: '',
      email: '',
      phone: '',
      address: '',
      logo: null,
    },

    // Client info
    client: {
      name: '',
      email: '',
      address: '',
    },

    // Invoice details
    invoice: {
      number: '',
      date: new Date().toISOString().split('T')[0],
      dueDate: '',
      notes: '',
    },

    // Line items
    items: [
      { description: '', quantity: 1, price: 0 },
    ],

    // Settings
    currency: 'USD',
    taxRate: 0,
    template: 'classic',

    // Discount settings
    discount: {
      type: 'percentage', // 'percentage' or 'fixed'
      value: 0,
    },

    // Computed values (updated reactively)
    get subtotal() {
      return this.items.reduce((sum, item) => {
        return sum + (parseFloat(item.quantity) || 0) * (parseFloat(item.price) || 0);
      }, 0);
    },

    get discountAmount() {
      const value = parseFloat(this.discount.value) || 0;
      if (this.discount.type === 'percentage') {
        return this.subtotal * value / 100;
      }
      return value;
    },

    get subtotalAfterDiscount() {
      return Math.max(0, this.subtotal - this.discountAmount);
    },

    get taxAmount() {
      return this.subtotalAfterDiscount * (parseFloat(this.taxRate) || 0) / 100;
    },

    get total() {
      return this.subtotalAfterDiscount + this.taxAmount;
    },

    // Initialize
    init() {
      // Check premium status
      this.isPremium = isPremium();

      // Load saved preferences
      const prefs = Storage.getPreferences();
      this.currency = prefs.currency || 'USD';
      this.taxRate = prefs.taxRate || 0;
      this.template = prefs.template || 'classic';

      // Load saved business info for premium users
      if (this.isPremium) {
        const savedBusiness = Storage.getBusinessInfo();
        if (savedBusiness.name) {
          this.business = { ...this.business, ...savedBusiness };
        }
      }

      // Generate default invoice number
      this.invoice.number = this.generateInvoiceNumber();

      // Set default due date (30 days from now)
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + 30);
      this.invoice.dueDate = dueDate.toISOString().split('T')[0];

      // Listen for premium status changes
      window.addEventListener('premiumStatusChanged', (e) => {
        this.isPremium = e.detail.isPremium;
      });

      // Handle ads visibility
      this.updateAdsVisibility();
    },

    // Generate invoice number
    generateInvoiceNumber() {
      const date = new Date();
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
      return `INV-${year}${month}-${random}`;
    },

    // Line items management
    addItem() {
      this.items.push({ description: '', quantity: 1, price: 0 });
    },

    removeItem(index) {
      if (this.items.length > 1) {
        this.items.splice(index, 1);
      }
    },

    // Format currency
    formatCurrency(amount) {
      return formatCurrency(amount, this.currency);
    },

    // Get currency symbol
    getCurrencySymbol() {
      const currency = getCurrency(this.currency);
      return currency.symbol;
    },

    // Save business info (premium feature)
    saveBusinessInfo() {
      if (!this.isPremium) {
        this.showPricingModal = true;
        return;
      }
      Storage.setBusinessInfo(this.business);
      this.showToast('Business info saved!', 'success');
    },

    // Load business info (premium feature)
    loadBusinessInfo() {
      if (!this.isPremium) {
        this.showPricingModal = true;
        return;
      }
      const saved = Storage.getBusinessInfo();
      if (saved.name) {
        this.business = { ...this.business, ...saved };
        this.showToast('Business info loaded!', 'success');
      } else {
        this.showToast('No saved business info found', 'error');
      }
    },

    // Handle logo upload (premium feature)
    handleLogoUpload(event) {
      if (!this.isPremium) {
        this.showPricingModal = true;
        event.target.value = '';
        return;
      }

      const file = event.target.files[0];
      if (!file) return;

      // Check file size (max 500KB)
      if (file.size > 500 * 1024) {
        this.showToast('Logo must be less than 500KB', 'error');
        event.target.value = '';
        return;
      }

      // Check file type
      if (!file.type.startsWith('image/')) {
        this.showToast('Please upload an image file', 'error');
        event.target.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        this.business.logo = e.target.result;
      };
      reader.readAsDataURL(file);
    },

    // Remove logo
    removeLogo() {
      this.business.logo = null;
    },

    // Save preferences
    savePreferences() {
      Storage.setPreferences({
        currency: this.currency,
        taxRate: this.taxRate,
        template: this.template,
      });
    },

    // Currency change handler
    onCurrencyChange() {
      if (!this.isPremium && this.currency !== 'USD') {
        this.showPricingModal = true;
        this.currency = 'USD';
        return;
      }
      this.savePreferences();
    },

    // Template change handler
    onTemplateChange(template) {
      if (!this.isPremium && template !== 'classic') {
        this.showPricingModal = true;
        return;
      }
      this.template = template;
      this.savePreferences();
    },

    // Generate and download PDF
    async downloadPDF() {
      if (this.isGeneratingPDF) return;

      // Basic validation
      if (!this.business.name || !this.client.name) {
        this.showToast('Please fill in business and client names', 'error');
        return;
      }

      if (this.items.every(item => !item.description)) {
        this.showToast('Please add at least one line item', 'error');
        return;
      }

      this.isGeneratingPDF = true;

      try {
        const previewElement = document.getElementById('invoice-preview');
        const filename = PDFGenerator.generateFilename(this.invoice.number, this.client.name);
        const addWatermark = !this.isPremium;

        await PDFGenerator.generate(previewElement, filename, addWatermark);
        this.showToast('Invoice downloaded successfully!', 'success');
      } catch (error) {
        console.error('PDF generation failed:', error);
        this.showToast('Failed to generate PDF. Please try again.', 'error');
      } finally {
        this.isGeneratingPDF = false;
      }
    },

    // Print invoice
    printInvoice() {
      window.print();
    },

    // Open Paddle checkout
    openCheckout(plan) {
      this.showPricingModal = false;
      PaddleHandler.openCheckout(plan);
    },

    // Cancel subscription
    cancelSubscription() {
      PaddleHandler.cancelSubscription();
    },

    // Update ads visibility based on premium status
    updateAdsVisibility() {
      const adContainers = document.querySelectorAll('.ad-container');
      adContainers.forEach(ad => {
        if (this.isPremium) {
          ad.classList.add('hidden-premium');
        } else {
          ad.classList.remove('hidden-premium');
        }
      });
    },

    // Toast notification
    showToast(message, type = 'success') {
      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      toast.textContent = message;
      document.body.appendChild(toast);

      // Animate in
      setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
      }, 10);

      // Remove after 3 seconds
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    },

    // Form validation
    validateForm() {
      const errors = [];

      if (!this.business.name.trim()) {
        errors.push('Business name is required');
      }
      if (!this.client.name.trim()) {
        errors.push('Client name is required');
      }
      if (!this.invoice.number.trim()) {
        errors.push('Invoice number is required');
      }
      if (this.items.every(item => !item.description.trim())) {
        errors.push('At least one line item is required');
      }

      return errors;
    },

    // Get template class
    getTemplateClass() {
      return `template-${this.template}`;
    },
  }));
});

// Debounce helper for preview updates
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
