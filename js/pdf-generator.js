// PDF Generation using jsPDF + html2canvas
const PDFGenerator = {
  generating: false,

  async generate(previewElement, filename = 'invoice.pdf', addWatermark = true) {
    if (this.generating) {
      console.log('PDF generation already in progress');
      return null;
    }

    this.generating = true;

    try {
      // Clone the preview element for PDF generation
      const clone = previewElement.cloneNode(true);
      clone.style.position = 'absolute';
      clone.style.left = '-9999px';
      clone.style.top = '0';
      clone.style.width = '210mm'; // A4 width
      clone.style.minHeight = '297mm'; // A4 height
      clone.style.padding = '20mm';
      clone.style.backgroundColor = '#ffffff';
      clone.style.boxSizing = 'border-box';

      // Remove any hidden elements or loading states
      clone.querySelectorAll('[x-cloak], .loading').forEach(el => el.remove());

      document.body.appendChild(clone);

      // Use html2canvas with high quality settings
      const canvas = await html2canvas(clone, {
        scale: 2, // Higher resolution for sharp PDFs
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        logging: false,
        windowWidth: clone.scrollWidth,
        windowHeight: clone.scrollHeight,
      });

      // Remove the clone
      document.body.removeChild(clone);

      // Calculate dimensions for A4
      const imgWidth = 210; // A4 width in mm
      const pageHeight = 297; // A4 height in mm
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      // Create PDF
      const pdf = new jspdf.jsPDF({
        orientation: imgHeight > pageHeight ? 'portrait' : 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      let heightLeft = imgHeight;
      let position = 0;

      // Add image to PDF (handle multiple pages if needed)
      const imgData = canvas.toDataURL('image/png');
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      // Add watermark for free users
      if (addWatermark) {
        this.addWatermark(pdf);
      }

      // Save the PDF
      pdf.save(filename);

      return true;
    } catch (error) {
      console.error('PDF generation error:', error);
      alert('Error generating PDF. Please try again.');
      return false;
    } finally {
      this.generating = false;
    }
  },

  addWatermark(pdf) {
    const pageCount = pdf.internal.getNumberOfPages();

    for (let i = 1; i <= pageCount; i++) {
      pdf.setPage(i);

      // Watermark styling
      pdf.setFontSize(10);
      pdf.setTextColor(150, 150, 150);

      // Position at bottom center
      const pageWidth = pdf.internal.pageSize.getWidth();
      const text = 'Made with MakeInvoice.online';
      const textWidth = pdf.getStringUnitWidth(text) * 10 / pdf.internal.scaleFactor;
      const x = (pageWidth - textWidth) / 2;
      const y = pdf.internal.pageSize.getHeight() - 10;

      pdf.text(text, x, y);
    }
  },

  // Generate filename from invoice data
  generateFilename(invoiceNumber, clientName) {
    const sanitize = (str) => str.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const date = new Date().toISOString().split('T')[0];

    if (invoiceNumber && clientName) {
      return `invoice_${sanitize(invoiceNumber)}_${sanitize(clientName)}_${date}.pdf`;
    } else if (invoiceNumber) {
      return `invoice_${sanitize(invoiceNumber)}_${date}.pdf`;
    }
    return `invoice_${date}.pdf`;
  },
};
