import telebot
from app.core.logger import logger
from app.core.config import config
from app.core.database import db
from app.fetchers.mail_fetcher import MailFetcher
from app.parsers.dispatcher import ReceiptParserDispatcher
from app.exporters.google_auth import get_google_client
from app.exporters.spreadsheet import UserSpreadsheet
from app.parsers.qr_parser import scan_qr_from_bytes
from app.fetchers.proverka_cheka_api import ProverkaChekaAPI
from app.parsers.proverka_cheka_parser import ProverkaChekaParser


def main():
    logger.info("Starting ReceiptsHub processing pipeline...")

    email_login = config.EMAIL_LOGIN
    password = config.EMAIL_PASSWORD
    server = config.IMAP_SERVER

    if not all([email_login, password, server]):
        logger.error("Missing email credentials in the configuration.")
        return

    fetcher = MailFetcher(email_address=email_login, password=password, imap_server=server)
    dispatcher = ReceiptParserDispatcher()
    api_client = ProverkaChekaAPI()
    bot = telebot.TeleBot(config.BOT_TOKEN)

    unread_receipts = fetcher.get_unread_receipts()

    if not unread_receipts:
        logger.info("Pipeline finished. No new receipts to process.")
        return

    try:
        g_client = get_google_client()
    except Exception as e:
        logger.error(f"Failed to connect to Google API: {e}")
        return

    for receipt_data in unread_receipts:
        subject = receipt_data.get("subject", "Чек")
        html_content = receipt_data["html"]
        images = receipt_data.get("images", [])
        from_email = receipt_data["from_email"]
        to_email = receipt_data["to_email"]

        user_data = db.get_user_by_email(from_email) or db.get_user_by_email(to_email)

        if not user_data:
            logger.warning(f"User not found for emails: From={from_email}, To={to_email}. Skipped.")
            continue

        tg_id, sheet_id = user_data
        logger.info(f"User identified: tg_id={tg_id}. Routing to sheet: {sheet_id}")

        receipt = dispatcher.parse_html(html_content)

        if not receipt and images:
            logger.info("HTML parsing failed. Trying to scan QR-code from email images...")
            for img_bytes in images:
                raw_qr_string = scan_qr_from_bytes(img_bytes)

                if raw_qr_string:
                    logger.info(f"QR found! Sending to API: {raw_qr_string}")
                    json_response = api_client.get_receipt_from_raw(raw_qr_string)
                    receipt = ProverkaChekaParser.parse(json_response)

                    if receipt:
                        break

        if receipt:
            saved = db.save_receipt(tg_id=tg_id, receipt=receipt)
            if saved:
                try:
                    logger.info(f"Exporting receipt {receipt.id} to Google Sheets...")
                    doc = UserSpreadsheet(g_client, spreadsheet_id=sheet_id)
                    receipts_page = doc.get_receipts_tab()
                    receipts_page.append_nested_receipt(receipt)
                except Exception as e:
                    logger.error(f"Failed to export receipt to Google Sheets: {e}")
            else:
                logger.info(f"Receipt {receipt.id} already exists in DB. Skipped export.")
        else:
            logger.warning(f"Could not parse email: {subject}")
            bot.send_message(
                tg_id,
                f"**Не удалось обработать чек**\n\n"
                f"Мне пришло письмо: *«{subject}»*, но я не смог найти в нём данные чека или прочитать QR-код.\n\n"
                f"Попробуй отсканировать QR-код с бумажного чека и прислать мне фото.",
                parse_mode="Markdown"
            )

    logger.info("Pipeline executed successfully!")


if __name__ == "__main__":
    main()