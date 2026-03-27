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

    def get_unread_receipts(self) -> list[str]:
        receipts_data = []
        mail = None
        try:
            logger.info(f"Connecting to {self.imap_server} to fetch unread receipts...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.password)
            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                logger.info("No new unread emails found.")
                return receipts_data

            mail_ids = messages[0].split()
            logger.info(f"Found {len(mail_ids)} unread emails. Checking for receipts...")

            for i in mail_ids:
                res, msg_data = mail.fetch(i, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = self._decode_str(msg.get("Subject", ""))

                        if "чек" in subject.lower():
                            raw_from = self._decode_str(msg.get("From", ""))
                            raw_to = self._decode_str(msg.get("To", ""))
                            sender_addr = email.utils.parseaddr(raw_from)[1]
                            to_addr = email.utils.parseaddr(raw_to)[1]

                            logger.info(f"Processing receipt email: {subject} (From: {sender_addr}, To: {to_addr})")

                            html_content = ""
                            images = []

                            for part in msg.walk():
                                content_type = part.get_content_type()

                                if content_type == "text/html":
                                    charset = part.get_content_charset() or 'utf-8'
                                    html_content = part.get_payload(decode=True).decode(charset, errors='ignore')

                                elif part.get_content_maintype() == 'image':
                                    img_data = part.get_payload(decode=True)
                                    if img_data:
                                        images.append(img_data)

                            receipts_data.append({
                                "subject": subject,
                                "html": html_content,
                                "images": images,
                                "from_email": sender_addr,
                                "to_email": to_addr
                            })

            logger.info(f"Successfully extracted {len(receipts_data)} receipts.")
            return receipts_data


        except Exception as e:
            logger.error(f"Error during email fetching: {e}")
            return receipts_data
        finally:
            if mail:
                try:
                    mail.logout()
                except:
                    pass