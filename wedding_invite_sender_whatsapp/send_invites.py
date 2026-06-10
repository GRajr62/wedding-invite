from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DEFAULT_STATUS_HEADER = "Status"
CHAT_READY_TIMEOUT_MS = 30_000
SHORT_TIMEOUT_MS = 3_000
PREVIEW_TIMEOUT_MS = 15_000
SEND_TIMEOUT_MS = 20_000
CLICK_TIMEOUT_MS = 1_000


class EmptySheetError(ValueError):
    pass


@dataclass(frozen=True)
class EventConfig:
    key: str
    sheet_name: str
    template: str
    attachments: list[Path]


@dataclass(frozen=True)
class AppConfig:
    spreadsheet_id: str
    credentials_file: Path
    chrome_profile_dir: Path
    headless: bool
    country_code: str
    status_header: str
    dry_run: bool
    send_delay_seconds: float
    events: list[EventConfig]


@dataclass(frozen=True)
class LoadedEvent:
    event: EventConfig
    headers: list[str]
    rows: list[dict[str, Any]]


def load_config(config_path: Path) -> AppConfig:
    base_dir = config_path.parent
    with config_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    events = []
    for key, event in raw["events"].items():
        events.append(
            EventConfig(
                key=key,
                sheet_name=event["sheet_name"],
                template=event["template"],
                attachments=[resolve_path(base_dir, value) for value in event.get("attachments", [])],
            )
        )

    return AppConfig(
        spreadsheet_id=raw["spreadsheet_id"],
        credentials_file=resolve_path(base_dir, raw["google_service_account_json"]),
        chrome_profile_dir=resolve_path(base_dir, raw.get("chrome_profile_dir", ".chrome-profile")),
        headless=bool(raw.get("headless", False)),
        country_code=str(raw.get("default_country_code", "91")),
        status_header=raw.get("status_header", DEFAULT_STATUS_HEADER),
        dry_run=bool(raw.get("dry_run", False)),
        send_delay_seconds=float(raw.get("send_delay_seconds", 2)),
        events=events,
    )


def resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path)


def get_sheets_service(credentials_file: Path) -> Any:
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=SCOPES,
    )
    return build("sheets", "v4", credentials=credentials)


def read_sheet_rows(
    service: Any,
    spreadsheet_id: str,
    sheet_name: str,
    status_header: str,
    ensure_status_column: bool,
) -> tuple[list[str], list[dict[str, Any]]]:
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_name}'")
        .execute()
    )
    values = response.get("values", [])
    if not values:
        raise EmptySheetError(f"Sheet tab '{sheet_name}' is empty.")

    headers = [header.strip() for header in values[0]]
    if status_header not in headers:
        headers.append(status_header)
        if ensure_status_column:
            status_column = column_letter(len(headers))
            (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_name}'!{status_column}1",
                    valueInputOption="RAW",
                    body={"values": [[status_header]]},
                )
                .execute()
            )

    rows: list[dict[str, Any]] = []
    for index, row_values in enumerate(values[1:], start=2):
        padded = row_values + [""] * (len(headers) - len(row_values))
        rows.append(
            {
                "row_number": index,
                "data": dict(zip(headers, padded)),
            }
        )
    return headers, rows


def column_letter(column_number: int) -> str:
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def update_status(
    service: Any,
    spreadsheet_id: str,
    sheet_name: str,
    status_column_index: int,
    row_number: int,
    status: str,
) -> None:
    status_cell = f"'{sheet_name}'!{column_letter(status_column_index)}{row_number}"
    (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=status_cell,
            valueInputOption="RAW",
            body={"values": [[status]]},
        )
        .execute()
    )


def normalize_phone(phone: str, default_country_code: str) -> str:
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return ""
    if len(digits) == 10:
        return f"{default_country_code}{digits}"
    return digits


def find_value(row: dict[str, Any], candidates: list[str]) -> str:
    normalized = {normalize_header(key): value for key, value in row.items()}
    for candidate in candidates:
        value = normalized.get(normalize_header(candidate))
        if value is not None:
            return str(value).strip()
    return ""


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def render_template(template: str, row: dict[str, Any]) -> str:
    normalized_row = {normalize_header(key): str(value) for key, value in row.items()}

    def replace(match: re.Match[str]) -> str:
        key = normalize_header(match.group(1))
        return normalized_row.get(key, "")

    return re.sub(r"\{([^{}]+)\}", replace, template)


def open_whatsapp(page):

    page.goto(
        "https://web.whatsapp.com/",
        wait_until="domcontentloaded"
    )

    print(
        "Open WhatsApp Web in the browser. "
        "Scan the QR code if needed."
    )

    try:

        page.wait_for_selector(
            "[data-testid='chat-list']",
            timeout=120_000
        )

        print("WhatsApp is ready.")

    except PlaywrightTimeoutError:

        raise TimeoutError(
            "WhatsApp Web was not ready within 120 seconds."
        )

def send_whatsapp_message(
    page: Page,
    phone: str,
    message: str,
    attachments: list[Path]
) -> None:

    page.goto(
        f"https://web.whatsapp.com/send?phone={phone}",
        wait_until="domcontentloaded",
    )
    page.locator("footer [contenteditable='true']").last.wait_for(timeout=CHAT_READY_TIMEOUT_MS)

    if not attachments:
        send_text_message(page, message)
        return

    for index, attachment in enumerate(attachments):

        if not attachment.exists():
            raise FileNotFoundError(
                f"Attachment not found: {attachment}"
            )

        print(f"Uploading: {attachment}")

        caption = message if index == 0 else ""
        upload_document_attachment(page, attachment, caption)


def send_text_message(page: Page, message: str) -> None:
    message_box = page.locator("footer [contenteditable='true']").last
    message_box.wait_for(timeout=60_000)
    message_box.fill(message)
    page.keyboard.press("Enter")
    wait_for_message_to_send(page)


def upload_document_attachment(page: Page, attachment: Path, caption: str) -> None:
    open_attachment_menu(page)

    if not choose_document_file(page, attachment):
        page.screenshot(path="document_option_not_found.png", full_page=True)
        print_visible_attach_menu_text(page)
        raise TimeoutError("Could not open WhatsApp document upload option.")

    if caption:
        fill_attachment_caption(page, caption)

    click_attachment_send(page)
    wait_for_attachment_preview_to_close(page, attachment)


def fill_attachment_caption(page: Page, caption: str) -> None:
    caption_boxes = [
        page.locator("[contenteditable='true'][aria-label='Type a message']").last,
        page.locator("[contenteditable='true'][role='textbox']").last,
        page.locator("[contenteditable='true']").last,
    ]

    for caption_box in caption_boxes:
        try:
            caption_box.wait_for(timeout=5_000)
            caption_box.click()
            caption_box.fill(caption)
            return
        except PlaywrightTimeoutError:
            continue

    page.screenshot(path="attachment_caption_not_found.png", full_page=True)
    raise TimeoutError("Could not find WhatsApp attachment caption box.")


def click_attachment_send(page: Page) -> None:
    if click_bottom_right_preview_button(page):
        return

    send_buttons = [
        page.get_by_role("button", name=re.compile(r"^Send$", re.IGNORECASE)).last,
        page.locator("[aria-label='Send']").last,
        page.locator("[data-icon='wds-ic-send-filled']").locator("xpath=ancestor::*[@role='button' or self::button][1]").last,
        page.locator("[data-icon='send']").locator("xpath=ancestor::*[@role='button' or self::button][1]").last,
        page.locator("[data-icon='send']").last,
    ]

    for send_button in send_buttons:
        try:
            send_button.wait_for(timeout=CLICK_TIMEOUT_MS)
            send_button.click()
            return
        except Exception:
            continue

    page.screenshot(path="attachment_send_button_not_found.png", full_page=True)
    raise TimeoutError("Could not find WhatsApp attachment send button.")


def click_bottom_right_preview_button(page: Page) -> bool:
    deadline = time.time() + 4
    while time.time() < deadline:
        box = page.evaluate(
            """
            () => {
                const candidates = [...document.querySelectorAll('button, [role="button"]')]
                    .map(element => {
                        const rect = element.getBoundingClientRect();
                        const style = window.getComputedStyle(element);
                        return { element, rect, style };
                    })
                    .filter(({ element, rect, style }) =>
                        rect.width >= 44 &&
                        rect.height >= 44 &&
                        rect.left > window.innerWidth * 0.75 &&
                        rect.top > window.innerHeight * 0.6 &&
                        !element.disabled &&
                        element.getAttribute('aria-disabled') !== 'true' &&
                        style.visibility !== 'hidden' &&
                        style.display !== 'none' &&
                        Number(style.opacity || 1) > 0.5
                    )
                    .sort((a, b) => b.rect.left - a.rect.left || b.rect.top - a.rect.top);

                const rect = candidates[0]?.rect;
                if (!rect) {
                    return null;
                }

                return {
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2
                };
            }
            """
        )
        if box:
            page.mouse.click(box["x"], box["y"])
            return True
        page.wait_for_timeout(100)

    return False


def wait_for_attachment_preview_to_close(page: Page, attachment: Path) -> None:
    try:
        page.get_by_text(attachment.name, exact=False).first.wait_for(state="hidden", timeout=SEND_TIMEOUT_MS)
        return
    except PlaywrightTimeoutError:
        pass

    try:
        page.locator("footer [contenteditable='true']").last.wait_for(timeout=SHORT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        page.screenshot(path="attachment_not_sent_after_click.png", full_page=True)
        raise TimeoutError("Clicked WhatsApp attachment send, but the attachment preview did not close.")


def open_attachment_menu(page: Page) -> None:
    attach_buttons = [
        page.locator("footer [aria-label='Attach'], footer [title='Attach']").locator("xpath=ancestor-or-self::*[@role='button' or self::button][1]").first,
        page.locator("footer [data-icon='plus'], footer [data-icon='clip']").locator("xpath=ancestor::*[@role='button' or self::button][1]").first,
        page.locator("footer [aria-label='Attach'], footer [title='Attach']").first,
        page.locator("footer [data-icon='plus'], footer [data-icon='clip']").first,
        page.locator("[aria-label='Attach'], [title='Attach']").last,
        page.locator("[data-icon='clip']").last,
    ]

    for attach_button in attach_buttons:
        try:
            attach_button.wait_for(timeout=2_000)
            attach_button.click(force=True)
            page.get_by_text("Document", exact=True).wait_for(timeout=SHORT_TIMEOUT_MS)
            return
        except PlaywrightTimeoutError:
            continue

    raise TimeoutError("Could not find WhatsApp attach button in the chat footer.")


def choose_document_file(page: Page, attachment: Path) -> bool:
    document_text = page.get_by_text("Document", exact=True).first
    try:
        document_text.wait_for(timeout=SHORT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return False

    document_options = [
        document_text.locator("xpath=ancestor::*[@role='button' or self::button or @tabindex][1]"),
        page.locator("[data-icon='attach-document']").locator("xpath=ancestor::*[@role='button' or self::button or @tabindex][1]").first,
        page.locator("[aria-label='Document'], [title='Document']").first,
        document_text,
    ]

    for document_option in document_options:
        if click_document_option_and_select_file(page, document_option, attachment):
            wait_for_attachment_preview(page, attachment)
            return True

    return False


def click_document_option_and_select_file(page: Page, document_option: Any, attachment: Path) -> bool:
    try:
        document_option.wait_for(timeout=SHORT_TIMEOUT_MS)
        with page.expect_file_chooser(timeout=5_000) as file_chooser_info:
            document_option.click(force=True)
        file_chooser_info.value.set_files(str(attachment))
        return True
    except PlaywrightTimeoutError:
        if set_document_input_file(page, attachment):
            return True
        return False


def wait_for_attachment_preview(page: Page, attachment: Path) -> None:
    filename = attachment.name
    try:
        page.get_by_text(filename, exact=False).first.wait_for(timeout=PREVIEW_TIMEOUT_MS)
        return
    except PlaywrightTimeoutError:
        pass

    try:
        page.locator("[aria-label='Send'], [data-icon='send']").last.wait_for(timeout=PREVIEW_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        page.screenshot(path="attachment_preview_not_loaded.png", full_page=True)
        raise TimeoutError(f"WhatsApp did not load the attachment preview for {filename}.")


def set_document_input_file(page: Page, attachment: Path) -> bool:
    file_inputs = page.locator("input[type='file']")
    try:
        file_inputs.first.wait_for(state="attached", timeout=5_000)
    except PlaywrightTimeoutError:
        return False

    for index in reversed(range(file_inputs.count())):
        file_input = file_inputs.nth(index)
        accept = (file_input.get_attribute("accept") or "").lower()
        if "image" not in accept and "video" not in accept:
            file_input.set_input_files(str(attachment))
            return True

    return False


def print_visible_attach_menu_text(page: Page) -> None:
    texts = page.locator("text=/\\S+/").evaluate_all(
        """
        elements => elements
            .filter(element => {
                const box = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return box.width > 0 && box.height > 0 && style.visibility !== 'hidden';
            })
            .map(element => element.textContent.trim())
            .filter(Boolean)
            .slice(-40)
        """
    )
    print(f"Visible text near attachment failure: {texts}")


def wait_for_message_to_send(page: Page) -> None:
    try:
        page.locator("span[data-icon='msg-time']").last.wait_for(state="detached", timeout=30_000)
    except PlaywrightTimeoutError:
        # WhatsApp changes internals often; reaching this point still means Enter was pressed.
        pass


def load_event_rows(service: Any, config: AppConfig, event: EventConfig) -> LoadedEvent | None:
    if not event.sheet_name.strip():
        print(f"\n{event.key}: sheet name is empty, skipping.")
        return None

    try:
        headers, rows = read_sheet_rows(
            service,
            config.spreadsheet_id,
            event.sheet_name,
            config.status_header,
            ensure_status_column=not config.dry_run,
        )
    except EmptySheetError as error:
        print(f"\n{error} Skipping {event.key}.")
        return None

    if not rows:
        print(f"\n{event.key}: no contact rows in '{event.sheet_name}', skipping.")
        return None

    return LoadedEvent(event=event, headers=headers, rows=rows)


def load_events_with_rows(service: Any, config: AppConfig) -> list[LoadedEvent]:
    loaded_events = []
    for event in config.events:
        loaded_event = load_event_rows(service, config, event)
        if loaded_event is not None:
            loaded_events.append(loaded_event)

    if not loaded_events:
        raise ValueError("All configured sheet tabs are empty or missing sheet names.")

    return loaded_events


def process_event(service: Any, page: Page | None, config: AppConfig, loaded_event: LoadedEvent) -> None:
    event = loaded_event.event
    status_column_index = loaded_event.headers.index(config.status_header) + 1

    print(f"\nReading {len(loaded_event.rows)} rows from '{event.sheet_name}'...")
    for row in loaded_event.rows:
        row_number = row["row_number"]
        data = row["data"]
        current_status = str(data.get(config.status_header, "")).strip().lower()
        if current_status.startswith("sent"):
            print(f"Row {row_number}: already sent, skipping.")
            continue

        name = find_value(data, ["name", "full name", "guest name"])
        phone = normalize_phone(find_value(data, ["phone", "phone number", "mobile", "mobile number", "whatsapp"]), config.country_code)
        if not phone:
            print(f"Row {row_number}: missing phone number, skipping.")
            continue

        message = render_template(event.template, data)
        print(f"Row {row_number}: sending {event.key} invite to {name or phone}...")
        if config.dry_run:
            print(f"DRY RUN -> phone={phone}, message={message!r}, attachments={event.attachments}")
            continue

        try:
            send_whatsapp_message(page, phone, message, event.attachments)
            print(f"Row {row_number}: WhatsApp message sent successfully.")
            sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_status(
                service,
                config.spreadsheet_id,
                event.sheet_name,
                status_column_index,
                row_number,
                f"Sent {event.key} {sent_at}",
            )
            print(f"Row {row_number}: status updated to sent.")
            time.sleep(config.send_delay_seconds)
        except Exception as error:
            print(f"Row {row_number}: failed, status not updated. Error: {error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send wedding and reception invites from Google Sheets via WhatsApp Web.")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config JSON. Defaults to wedding_invite_sender_whatsapp/config.json when run from this folder.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print rows/messages without sending WhatsApp messages or updating status.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    if args.dry_run:
        config = AppConfig(**{**config.__dict__, "dry_run": True})

    service = get_sheets_service(config.credentials_file)
    loaded_events = load_events_with_rows(service, config)

    if config.dry_run:
        for loaded_event in loaded_events:
            process_event(service, page=None, config=config, loaded_event=loaded_event)
        return

    with sync_playwright() as playwright:
        browser_context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.chrome_profile_dir),
            headless=config.headless,
            viewport={"width": 1366, "height": 768},
            args=["--window-position=0,0", "--window-size=1366,768"],
        )
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        open_whatsapp(page)

        for loaded_event in loaded_events:
            process_event(service, page, config, loaded_event)

        browser_context.close()


if __name__ == "__main__":
    main()
