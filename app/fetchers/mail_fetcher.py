import imaplib
import email
from email.header import decode_header
from app.core.logger import logger


class MailFetcher:
    def __init__(self, email_address: str, password: str, imap_server: str):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server

    def _decode_str(self, s):
        decoded, charset = decode_header(s)[0]
        if isinstance(decoded, bytes):
            return decoded.decode(charset or 'utf-8', errors='ignore')
        return decoded

    def test_connection(self):
        mail = None
        try:
            logger.info(f"Attempting to connect to {self.imap_server}...")

            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            logger.info("Successfully logged into the mailbox.")

            mail.select("inbox")

            status, messages = mail.search(None, "ALL")

            if status == "OK":
                mail_ids = messages[0].split()
                latest_ids = mail_ids[-3:]

                logger.info("Last 3 emails in the inbox:")
                for i in reversed(latest_ids):
                    res, msg_data = mail.fetch(i, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject = self._decode_str(msg.get("Subject", "No Subject"))
                            sender = self._decode_str(msg.get("From", "Unknown Sender"))

                            logger.info(f"Email: {subject} | From: {sender}")

            return True
        except Exception as e:
            logger.error(f"Failed to connect to the mailbox: {e}")
            return False
        finally:
            if mail:
                try:
                    mail.logout()
                except:
                    pass

    def get_unread_receipts(self) -> list[str]:
        receipts_html = []
        mail = None
        try:
            logger.info(f"Connecting to {self.imap_server} to fetch unread receipts...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                logger.info("No new unread emails found.")
                return receipts_html

            mail_ids = messages[0].split()
            logger.info(f"Found {len(mail_ids)} unread emails. Checking for receipts...")

            for i in mail_ids:
                res, msg_data = mail.fetch(i, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = self._decode_str(msg.get("Subject", ""))

                        if "чек" in subject.lower():
                            logger.info(f"Processing receipt email: {subject}")
                            for part in msg.walk():
                                if part.get_content_type() == "text/html":
                                    charset = part.get_content_charset() or 'utf-8'
                                    html_content = part.get_payload(decode=True).decode(charset, errors='ignore')
                                    receipts_html.append(html_content)
                                    break

            logger.info(f"Successfully extracted {len(receipts_html)} receipts.")
            return receipts_html

        except Exception as e:
            logger.error(f"Error during email fetching: {e}")
            return receipts_html
        finally:
            if mail:
                try:
                    mail.logout()
                except:
                    pass