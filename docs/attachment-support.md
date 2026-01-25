# Attachment Support

onKaul can process attachments from Slack and Jira messages.

## Slack Attachments

**Supported:**
- Images: PNG, JPG, GIF, WebP, BMP, TIFF → OCR text extraction
- Documents: PDF, TXT, LOG → Text extraction

**Required Slack Scope:**
- `files:read` - Download private files

**How it works:**
1. User uploads file in Slack message with @onkaul mention
2. Bot downloads file using Slack API
3. Extracts text (OCR for images, text extraction for PDFs)
4. Adds extracted text to investigation context
5. Agent can analyze screenshots, error logs, etc.

## Jira Attachments

**Supported:**
- Same file types as Slack
- Downloads from Jira REST API

**How it works:**
1. User attaches file to Jira issue
2. Bot fetches attachment list from issue
3. Downloads and processes files
4. Extracts text for agent context

## Installation Requirements

**Python packages** (already in requirements.txt):
- `pytesseract` - OCR wrapper
- `Pillow` - Image processing
- `PyMuPDF` - PDF text extraction

**System dependency - Tesseract OCR:**

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Verify installation
tesseract --version
```

## Examples

**Slack with screenshot:**
```
User: @onkaul this error keeps happening [uploads screenshot]
Bot: [downloads screenshot]
      [runs OCR to extract error text]
      [investigates the extracted error message]
      [responds with analysis]
```

**Slack with log file:**
```
User: @onkaul check this log [uploads error.log]
Bot: [downloads log file]
      [extracts text content]
      [analyzes logs for patterns]
      [responds with findings]
```

## Logging

When attachments are processed, you'll see:
```
📎 Found 2 attachment(s)
  - screenshot.png (png)
    ✅ Extracted 1234 chars
  - error.log (log)
    ✅ Extracted 5678 chars
📎 Adding attachment text to context...
  ✅ Added text from screenshot.png (1234 chars)
  ✅ Added text from error.log (5678 chars)
✅ Processed 2 attachment(s)
```

## Limitations

- Maximum 2000 chars per attachment added to context (to avoid token limits)
- Requires Tesseract installed on system for OCR
- Large files may timeout (30s download limit)
- Some file types not supported (binaries, archives, etc.)
