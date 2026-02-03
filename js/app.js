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
      const previewElement = document.getElementById('invoice-preview');
      if (!previewElement) {
        this.showToast('Could not find invoice preview', 'error');
        return;
      }

      // Create a hidden iframe for printing
      let printFrame = document.getElementById('print-frame');
      if (!printFrame) {
        printFrame = document.createElement('iframe');
        printFrame.id = 'print-frame';
        printFrame.style.position = 'absolute';
        printFrame.style.top = '-9999px';
        printFrame.style.left = '-9999px';
        document.body.appendChild(printFrame);
      }

      const printContent = `
        <!DOCTYPE html>
        <html>
        <head>
          <title>Invoice ${this.invoice.number || 'Print'}</title>
          <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, -apple-system, sans-serif; padding: 40px; }
            .invoice-preview { background: white; }
            .text-gray-900 { color: #111827; }
            .text-gray-800 { color: #1f2937; }
            .text-gray-700 { color: #374151; }
            .text-gray-600 { color: #4b5563; }
            .text-gray-500 { color: #6b7280; }
            .text-gray-400 { color: #9ca3af; }
            .text-green-600 { color: #059669; }
            .text-blue-600 { color: #2563eb; }
            .text-blue-100 { color: #dbeafe; }
            .text-white { color: white; }
            .font-bold { font-weight: 700; }
            .font-semibold { font-weight: 600; }
            .font-medium { font-weight: 500; }
            .text-2xl { font-size: 1.5rem; }
            .text-3xl { font-size: 1.875rem; }
            .text-lg { font-size: 1.125rem; }
            .text-sm { font-size: 0.875rem; }
            .text-xs { font-size: 0.75rem; }
            .uppercase { text-transform: uppercase; }
            .tracking-wider { letter-spacing: 0.05em; }
            .whitespace-pre-line { white-space: pre-line; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .flex { display: flex; }
            .justify-between { justify-content: space-between; }
            .justify-end { justify-content: flex-end; }
            .items-start { align-items: flex-start; }
            .mt-8 { margin-top: 2rem; }
            .mb-2 { margin-bottom: 0.5rem; }
            .mb-4 { margin-bottom: 1rem; }
            .mb-6 { margin-bottom: 1.5rem; }
            .mb-8 { margin-bottom: 2rem; }
            .py-2 { padding-top: 0.5rem; padding-bottom: 0.5rem; }
            .py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
            .pt-4 { padding-top: 1rem; }
            .pt-6 { padding-top: 1.5rem; }
            .pb-4 { padding-bottom: 1rem; }
            .border-b { border-bottom: 1px solid #e5e7eb; }
            .border-b-2 { border-bottom: 2px solid #1f2937; }
            .border-t { border-top: 1px solid #e5e7eb; }
            .border-t-2 { border-top: 2px solid #1f2937; }
            .border-gray-100 { border-color: #f3f4f6; }
            .border-gray-200 { border-color: #e5e7eb; }
            .border-gray-800 { border-color: #1f2937; }
            .w-full { width: 100%; }
            .w-64 { width: 16rem; }
            .w-20 { width: 5rem; }
            .w-28 { width: 7rem; }
            table { width: 100%; border-collapse: collapse; }
            th { text-align: left; font-size: 0.875rem; font-weight: 600; color: #4b5563; padding: 0.5rem 0; border-bottom: 2px solid #e5e7eb; }
            td { padding: 0.75rem 0; border-bottom: 1px solid #f3f4f6; }
            .logo-preview, img { max-height: 4rem; object-fit: contain; }
            .invoice-header { border-bottom: 2px solid #1f2937; padding-bottom: 1rem; margin-bottom: 1.5rem; display: flex; justify-content: space-between; }
            @media print { body { padding: 20px; } }
          </style>
        </head>
        <body>
          ${previewElement.innerHTML}
        </body>
        </html>
      `;

      const frameDoc = printFrame.contentWindow || printFrame.contentDocument;
      const doc = frameDoc.document || frameDoc;
      doc.open();
      doc.write(printContent);
      doc.close();

      // Wait for content to load, then print
      setTimeout(() => {
        printFrame.contentWindow.focus();
        printFrame.contentWindow.print();
      }, 250);
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
