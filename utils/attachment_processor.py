"""Process attachments from Slack and Jira."""

import tempfile
from pathlib import Path

import httpx


class AttachmentProcessor:
    """Process attachments (images, PDFs, etc.) from Slack and Jira."""

    def __init__(self):
        self.supported_image_types = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff"}
        self.supported_doc_types = {"pdf", "txt", "log"}

    def process_slack_file(self, file_data: dict, slack_token: str) -> dict:
        """
        Download and process a Slack file.

        Args:
            file_data: File object from Slack event
            slack_token: Slack bot token for authentication

        Returns:
            Dict with file info and extracted text (if applicable)
        """
        url = file_data.get("url_private")
        filename = file_data.get("name", "unknown")
        mimetype = file_data.get("mimetype", "")
        filetype = file_data.get("filetype", "").lower()

        if not url:
            return {"error": "No download URL in file data"}

        try:
            # Download file
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {slack_token}"},
                timeout=30.0,
            )
            response.raise_for_status()
            file_bytes = response.content

            # Process based on type
            result = {
                "filename": filename,
                "mimetype": mimetype,
                "filetype": filetype,
                "size": len(file_bytes),
            }

            # Extract text if image
            if filetype in self.supported_image_types:
                text = self._extract_text_from_image(file_bytes)
                result["extracted_text"] = text
                result["processed"] = True

            # Extract text if PDF/text
            elif filetype in self.supported_doc_types:
                text = self._extract_text_from_doc(file_bytes, filetype)
                result["extracted_text"] = text
                result["processed"] = True

            else:
                result["processed"] = False
                result["message"] = f"Unsupported file type: {filetype}"

            return result

        except Exception as e:
            return {"error": f"Failed to process file: {str(e)}"}

    def process_jira_attachment(self, attachment_data: dict, jira_auth: tuple) -> dict:
        """
        Download and process a Jira attachment.

        Args:
            attachment_data: Attachment object from Jira
            jira_auth: (email, api_token) tuple

        Returns:
            Dict with file info and extracted text (if applicable)
        """
        url = attachment_data.get("content")
        filename = attachment_data.get("filename", "unknown")
        mimetype = attachment_data.get("mimeType", "")

        if not url:
            return {"error": "No download URL in attachment data"}

        try:
            # Download file
            response = httpx.get(url, auth=jira_auth, timeout=30.0)
            response.raise_for_status()
            file_bytes = response.content

            # Determine file type
            ext = Path(filename).suffix.lstrip(".").lower()

            result = {
                "filename": filename,
                "mimetype": mimetype,
                "size": len(file_bytes),
            }

            # Extract text if image
            if ext in self.supported_image_types:
                text = self._extract_text_from_image(file_bytes)
                result["extracted_text"] = text
                result["processed"] = True

            # Extract text if PDF/text
            elif ext in self.supported_doc_types:
                text = self._extract_text_from_doc(file_bytes, ext)
                result["extracted_text"] = text
                result["processed"] = True

            else:
                result["processed"] = False
                result["message"] = f"Unsupported file type: {ext}"

            return result

        except Exception as e:
            return {"error": f"Failed to process attachment: {str(e)}"}

    def _extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from image using Tesseract OCR.

        Args:
            image_bytes: Image file bytes

        Returns:
            Extracted text
        """
        try:
            from io import BytesIO

            import pytesseract
            from PIL import Image

            # Load image
            image = Image.open(BytesIO(image_bytes))

            # Run OCR
            text = pytesseract.image_to_string(image)

            return text.strip()

        except ImportError:
            return "[OCR not available - install pytesseract and PIL]"
        except Exception as e:
            return f"[OCR failed: {str(e)}]"

    def _extract_text_from_doc(self, doc_bytes: bytes, filetype: str) -> str:
        """
        Extract text from document (PDF, txt, log).

        Args:
            doc_bytes: Document file bytes
            filetype: File extension (pdf, txt, log)

        Returns:
            Extracted text
        """
        if filetype == "txt" or filetype == "log":
            try:
                return doc_bytes.decode("utf-8")
            except Exception as e:
                return f"[Failed to decode text: {str(e)}]"

        elif filetype == "pdf":
            try:
                import fitz  # PyMuPDF

                # Write to temp file (PyMuPDF needs file path)
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(doc_bytes)
                    tmp_path = tmp.name

                # Extract text
                doc = fitz.open(tmp_path)
                text_parts = []
                for page in doc:
                    text_parts.append(page.get_text())
                doc.close()

                # Clean up
                Path(tmp_path).unlink()

                return "\n".join(text_parts)

            except ImportError:
                return "[PDF processing not available - install PyMuPDF]"
            except Exception as e:
                return f"[PDF extraction failed: {str(e)}]"

        return "[Unsupported document type]"


# Singleton instance
attachment_processor = AttachmentProcessor()
