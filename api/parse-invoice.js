// Vercel Serverless Function for parsing invoice prompts with Claude API
// POST /api/parse-invoice

export default async function handler(req, res) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Validate request body
  const { prompt } = req.body;
  if (!prompt || typeof prompt !== 'string') {
    return res.status(400).json({ error: 'Missing or invalid prompt' });
  }

  // Sanitize prompt - limit length and remove potentially dangerous content
  const sanitizedPrompt = prompt
    .trim()
    .slice(0, 500) // Limit to 500 characters
    .replace(/<[^>]*>/g, ''); // Remove HTML tags

  if (sanitizedPrompt.length < 5) {
    return res.status(400).json({ error: 'Prompt too short. Please provide more details.' });
  }

  // Get API key from environment
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error('ANTHROPIC_API_KEY not configured');
    return res.status(500).json({ error: 'Server configuration error' });
  }

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-3-haiku-20240307',
        max_tokens: 1024,
        system: `You are an invoice data extractor. Parse the user's natural language request and extract invoice information. Return ONLY valid JSON with this exact structure:

{
  "client": {
    "name": "string or null",
    "email": "string or null",
    "address": "string or null"
  },
  "items": [
    {
      "description": "string",
      "quantity": number,
      "price": number
    }
  ],
  "invoice": {
    "notes": "string or null"
  }
}

Rules:
- Extract client name, email if mentioned
- Parse line items with description, quantity, and unit price
- For hourly rates like "$75/hour for 8 hours", set quantity=8 and price=75
- For total amounts like "$500 for web design", set quantity=1 and price=500
- For multiple items like "3 widgets at $25 each", set quantity=3 and price=25
- Always return valid JSON, nothing else
- If you can't parse something, use null for optional fields
- Always include at least one item`,
        messages: [
          {
            role: 'user',
            content: sanitizedPrompt,
          },
        ],
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Claude API error:', response.status, errorData);
      return res.status(500).json({
        error: 'Failed to process your request. Please try again.',
        details: process.env.NODE_ENV === 'development' ? errorData : undefined
      });
    }

    const data = await response.json();

    // Extract the text content from Claude's response
    const textContent = data.content?.find(c => c.type === 'text');
    if (!textContent || !textContent.text) {
      return res.status(500).json({ error: 'Invalid response from AI' });
    }

    // Parse the JSON response
    let parsedData;
    try {
      // Remove any markdown code block formatting if present
      let jsonText = textContent.text.trim();
      if (jsonText.startsWith('```json')) {
        jsonText = jsonText.slice(7);
      } else if (jsonText.startsWith('```')) {
        jsonText = jsonText.slice(3);
      }
      if (jsonText.endsWith('```')) {
        jsonText = jsonText.slice(0, -3);
      }
      jsonText = jsonText.trim();

      parsedData = JSON.parse(jsonText);
    } catch (parseError) {
      console.error('Failed to parse Claude response:', textContent.text);
      return res.status(500).json({
        error: "I couldn't understand that. Try: 'Invoice [name] for [amount] [service]'"
      });
    }

    // Validate the parsed data structure
    if (!parsedData.items || !Array.isArray(parsedData.items) || parsedData.items.length === 0) {
      return res.status(400).json({
        error: "I couldn't identify any items. Try: 'Invoice Bob for $500 web design'"
      });
    }

    // Ensure all items have required fields with defaults
    parsedData.items = parsedData.items.map(item => ({
      description: item.description || 'Service',
      quantity: parseFloat(item.quantity) || 1,
      price: parseFloat(item.price) || 0,
    }));

    // Ensure client object exists
    parsedData.client = {
      name: parsedData.client?.name || null,
      email: parsedData.client?.email || null,
      address: parsedData.client?.address || null,
    };

    // Ensure invoice object exists
    parsedData.invoice = {
      notes: parsedData.invoice?.notes || null,
    };

    return res.status(200).json(parsedData);

  } catch (error) {
    console.error('Server error:', error);
    return res.status(500).json({
      error: 'Connection failed. Check your internet and try again.'
    });
  }
}
