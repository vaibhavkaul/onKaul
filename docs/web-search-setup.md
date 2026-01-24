# Web Search Setup Guide

The `web_search` tool uses Google Custom Search API to search the web for documentation, Stack Overflow answers, and library information.

## Google Custom Search Setup

### Step 1: Get API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Custom Search API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Custom Search API"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy the API key

### Step 2: Create Custom Search Engine

1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click "Add" or "Create new search engine"
3. Configure:
   - **Sites to search**: Select "Search the entire web"
   - **Name**: "onKaul Web Search" (or whatever you want)
4. Click "Create"
5. Go to "Control Panel" for your search engine
6. Copy the **Search engine ID** (looks like: `a1b2c3d4e5f6g7h8i`)

### Step 3: Configure Environment

Add to your `.env` file:

```bash
# Google Custom Search
GOOGLE_SEARCH_API_KEY=AIzaSy...your-api-key
GOOGLE_SEARCH_ENGINE_ID=a1b2c3d4e5f6g7h8i
```

### Step 4: Test

```bash
# Restart server
uv run uvicorn main:app --reload --port 8000

# Test with a query that needs web search
# Example: "@onkaul how do I use React hooks?"
```

## Pricing

**Google Custom Search API:**
- Free tier: 100 queries/day
- Paid: $5 per 1000 queries (after free tier)
- [Pricing details](https://developers.google.com/custom-search/v1/overview#pricing)

## Alternative: Brave Search API

If you prefer Brave Search (better privacy, higher free tier):

### Setup

1. Go to [Brave Search API](https://brave.com/search/api/)
2. Sign up and get API key
3. Update `clients/websearch.py` to use Brave instead:

```python
# Use Brave API instead of Google
self.base_url = "https://api.search.brave.com/res/v1/web/search"
# ... (implementation similar to Google)
```

**Pricing:**
- Free tier: 2,000 queries/month
- Paid: $5 per 1000 queries

## When Web Search is Used

The agent automatically uses web search when:
- Investigating errors with external libraries
- Looking up documentation for frameworks
- Searching Stack Overflow for known issues
- Finding API documentation

The agent knows to prefer internal tools (GitHub search, Jira) for TapTap Send code and only use web search for external resources.
