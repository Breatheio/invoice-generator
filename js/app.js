// Main Alpine.js application
document.addEventListener('alpine:init', () => {
  Alpine.data('invoiceApp', () => ({
    // App state
    isPremium: false,
    isGeneratingPDF: false,
    showPricingModal: false,
    showHistoryModal: false,
    showSuccessModal: false,
    activeTab: 'form', // 'form' or 'preview' for mobile
    draftRestored: false,
    lastSaved: null,
    invoiceHistory: [],

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

      // Try to restore draft first
      const draft = Storage.getDraft();
      if (draft) {
        this.loadDraft(draft);
        this.draftRestored = true;
        setTimeout(() => {
          this.showToast('Draft restored! Your previous work has been loaded.', 'success');
        }, 500);
      } else {
        // Load saved business info for premium users (only if no draft)
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
      }

      // Listen for premium status changes
      window.addEventListener('premiumStatusChanged', (e) => {
        this.isPremium = e.detail.isPremium;
      });

      // Handle ads visibility
      this.updateAdsVisibility();

      // Load invoice history
      this.loadHistory();

      // Set up auto-save (debounced)
      this.$watch('business', () => this.debouncedSaveDraft(), { deep: true });
      this.$watch('client', () => this.debouncedSaveDraft(), { deep: true });
      this.$watch('invoice', () => this.debouncedSaveDraft(), { deep: true });
      this.$watch('items', () => this.debouncedSaveDraft(), { deep: true });
      this.$watch('discount', () => this.debouncedSaveDraft(), { deep: true });
      this.$watch('currency', () => this.debouncedSaveDraft());
      this.$watch('taxRate', () => this.debouncedSaveDraft());
    },

    // Generate invoice number
    generateInvoiceNumber() {
      const date = new Date();
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
      return `INV-${year}${month}-${random}`;
    },

    // Auto-save draft
    _saveTimeout: null,

    saveDraft() {
      const draft = {
        business: this.business,
        client: this.client,
        invoice: this.invoice,
        items: this.items,
        discount: this.discount,
        currency: this.currency,
        taxRate: this.taxRate,
      };
      Storage.setDraft(draft);
      this.lastSaved = new Date();
      console.log('Draft saved:', new Date().toLocaleTimeString());
    },

    // Debounced save (waits 1 second after last change)
    debouncedSaveDraft() {
      clearTimeout(this._saveTimeout);
      this._saveTimeout = setTimeout(() => {
        this.saveDraft();
      }, 1000);
    },

    // Load draft data
    loadDraft(draft) {
      if (draft.business) this.business = { ...this.business, ...draft.business };
      if (draft.client) this.client = { ...this.client, ...draft.client };
      if (draft.invoice) this.invoice = { ...this.invoice, ...draft.invoice };
      if (draft.items && draft.items.length > 0) this.items = draft.items;
      if (draft.discount) this.discount = { ...this.discount, ...draft.discount };
      if (draft.currency) this.currency = draft.currency;
      if (draft.taxRate !== undefined) this.taxRate = draft.taxRate;
    },

    // Start new invoice (clear draft)
    newInvoice() {
      if (!confirm('Start a new invoice? Your current draft will be cleared.')) {
        return;
      }

      // Clear draft from storage
      Storage.clearDraft();

      // Reset all fields
      this.business = {
        name: '',
        email: '',
        phone: '',
        address: '',
        logo: null,
      };
      this.client = {
        name: '',
        email: '',
        address: '',
      };
      this.invoice = {
        number: this.generateInvoiceNumber(),
        date: new Date().toISOString().split('T')[0],
        dueDate: (() => {
          const d = new Date();
          d.setDate(d.getDate() + 30);
          return d.toISOString().split('T')[0];
        })(),
        notes: '',
      };
      this.items = [{ description: '', quantity: 1, price: 0 }];
      this.discount = { type: 'percentage', value: 0 };
      this.taxRate = 0;

      // Load business info for premium users
      if (this.isPremium) {
        const savedBusiness = Storage.getBusinessInfo();
        if (savedBusiness.name) {
          this.business = { ...this.business, ...savedBusiness };
        }
      }

      this.draftRestored = false;
      this.showToast('New invoice started', 'success');
    },

    // Invoice History
    openHistory() {
      this.invoiceHistory = Storage.getHistory();
      this.showHistoryModal = true;
    },

    loadHistory() {
      this.invoiceHistory = Storage.getHistory();
    },

    saveToHistory() {
      const invoiceData = {
        business: this.business,
        client: this.client,
        invoice: this.invoice,
        items: this.items,
        discount: this.discount,
        currency: this.currency,
        taxRate: this.taxRate,
        total: this.total,
      };

      Storage.addToHistory(invoiceData);
      this.loadHistory();
      this.showToast('Invoice saved to history!', 'success');
    },

    loadFromHistory(id) {
      const item = Storage.getHistoryItem(id);
      if (!item || !item.data) {
        this.showToast('Could not load invoice', 'error');
        return;
      }

      // Load the invoice data
      this.loadDraft(item.data);
      this.showHistoryModal = false;
      this.showToast('Invoice loaded from history', 'success');
    },

    duplicateFromHistory(id) {
      const item = Storage.getHistoryItem(id);
      if (!item || !item.data) {
        this.showToast('Could not duplicate invoice', 'error');
        return;
      }

      // Load the invoice data
      this.loadDraft(item.data);

      // Generate new invoice number
      this.invoice.number = this.generateInvoiceNumber();

      // Set today's date
      this.invoice.date = new Date().toISOString().split('T')[0];

      // Set due date to 30 days from now
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + 30);
      this.invoice.dueDate = dueDate.toISOString().split('T')[0];

      this.showHistoryModal = false;
      this.showToast('Invoice duplicated with new number and dates', 'success');
    },

    deleteFromHistory(id) {
      if (!confirm('Delete this invoice from history?')) return;
      Storage.removeFromHistory(id);
      this.loadHistory();
      this.showToast('Invoice deleted from history', 'success');
    },

    clearAllHistory() {
      if (!confirm('Delete ALL invoices from history? This cannot be undone.')) return;
      Storage.clearHistory();
      this.loadHistory();
      this.showToast('History cleared', 'success');
    },

    formatHistoryDate(isoString) {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
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

        // Show success modal with ad for free users, just toast for premium
        if (!this.isPremium) {
          this.showSuccessModal = true;
        } else {
          this.showToast('Invoice downloaded successfully!', 'success');
        }
      } catch (error) {
        console.error('PDF generation failed:', error);
        this.showToast('Failed to generate PDF. Please try again.', 'error');
      } finally {
        this.isGeneratingPDF = false;
      }
    },

    // Print invoice
    printInvoice() {
      const preview = document.getElementById('invoice-preview');
      if (!preview) return;

      // Create print container
      const printContainer = document.createElement('div');
      printContainer.id = 'print-container';
      printContainer.innerHTML = preview.outerHTML;

      // Style it for printing
      printContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: white;
        z-index: 99999;
        padding: 20px;
        overflow: auto;
      `;

      // Hide original content and show print container
      document.body.style.overflow = 'hidden';
      document.body.appendChild(printContainer);

      // Print
      setTimeout(() => {
        window.print();
        // Remove print container after printing
        setTimeout(() => {
          printContainer.remove();
          document.body.style.overflow = '';
        }, 500);
      }, 100);
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

// Debounce helper - preserves 'this' context
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}
