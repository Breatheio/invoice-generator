// Currency data for invoice generator
const CURRENCIES = [
  { code: 'USD', symbol: '$', name: 'US Dollar', position: 'before' },
  { code: 'EUR', symbol: '€', name: 'Euro', position: 'before' },
  { code: 'GBP', symbol: '£', name: 'British Pound', position: 'before' },
  { code: 'ILS', symbol: '₪', name: 'Israeli Shekel', position: 'before' },
  { code: 'CAD', symbol: 'CA$', name: 'Canadian Dollar', position: 'before' },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', position: 'before' },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen', position: 'before', decimals: 0 },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan', position: 'before' },
  { code: 'INR', symbol: '₹', name: 'Indian Rupee', position: 'before' },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc', position: 'before' },
  { code: 'SEK', symbol: 'kr', name: 'Swedish Krona', position: 'after' },
  { code: 'NOK', symbol: 'kr', name: 'Norwegian Krone', position: 'after' },
  { code: 'DKK', symbol: 'kr', name: 'Danish Krone', position: 'after' },
  { code: 'PLN', symbol: 'zł', name: 'Polish Zloty', position: 'after' },
  { code: 'BRL', symbol: 'R$', name: 'Brazilian Real', position: 'before' },
  { code: 'MXN', symbol: 'MX$', name: 'Mexican Peso', position: 'before' },
  { code: 'ZAR', symbol: 'R', name: 'South African Rand', position: 'before' },
  { code: 'SGD', symbol: 'S$', name: 'Singapore Dollar', position: 'before' },
  { code: 'HKD', symbol: 'HK$', name: 'Hong Kong Dollar', position: 'before' },
  { code: 'NZD', symbol: 'NZ$', name: 'New Zealand Dollar', position: 'before' },
];

function getCurrency(code) {
  return CURRENCIES.find(c => c.code === code) || CURRENCIES[0];
}

function formatCurrency(amount, currencyCode = 'USD') {
  const currency = getCurrency(currencyCode);
  const decimals = currency.decimals !== undefined ? currency.decimals : 2;
  const formattedAmount = Number(amount).toFixed(decimals);

  if (currency.position === 'after') {
    return `${formattedAmount} ${currency.symbol}`;
  }
  return `${currency.symbol}${formattedAmount}`;
}
