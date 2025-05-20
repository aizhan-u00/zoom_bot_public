"""
Telegram bot for managing Zoom meetings and uploading recordings to YouTube.

Implements a user interface using aiogram for booking, viewing, deleting Zoom 
meetings, and uploading recordings to YouTube. Integrates with ZoomManager, 
YouTubeManager, and DataBase to perform operations.
"""
import re
import os
from datetime import datetime
import asyncio
import pytz
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from logger import logger
from config import BOT_TOKEN, TIMEZONE
from zoom_manager import ZoomManager
from youtube_manager import YouTubeManager
from database import DataBase

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
zoom_manager = ZoomManager()
db = DataBase()
youtube_manager = YouTubeManager()
timezone = pytz.timezone(TIMEZONE)


class BotStates(StatesGroup):
    """FSM states for bot operations."""

    idle = State()
    booking = State()
    deleting = State()
    uploading = State()


async def send_welcome(chat_id: int) -> None:
    """Sends a welcome message with commands.

    Args:
        chat_id (int): Telegram chat ID.
    """
    message = (
        "👋 Welcome!\n"
        "Commands:\n"
        "/book - Book a meeting\n"
        "/my_meetings - My meetings\n"
        "/delete - Delete a meeting\n"
        "/upload_to_youtube - Upload recording to YouTube\n"
        "/cancel - Cancel operation"
    )
    await bot.send_message(chat_id, message)
    logger.info("Welcome message sent to user %s", chat_id)


async def cancel_operation(message: Message, state: FSMContext) -> None:
    """Cancels the current operation and clears the state.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    await state.clear()
    await bot.send_message(message.chat.id, "⛔ Operation canceled.")
    logger.info("Operation canceled for user %s", message.chat.id)


@router.message(Command("start", "help"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handles the /start and /help commands.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    await state.clear()
    await send_welcome(message.chat.id)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Handles the /cancel command.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    await cancel_operation(message, state)


@router.message(Command("book"))
async def cmd_book(message: Message, state: FSMContext) -> None:
    """Starts the meeting booking process.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    await state.set_state(BotStates.booking)
    await state.update_data(step="date")
    await bot.send_message(message.chat.id, "📅 Enter the date (DD.MM.YYYY):")
    logger.info("Starting booking for user %s", message.chat.id)


async def process_date(chat_id: int, text: str, state: FSMContext) -> None:
    """Processes date input for booking.

    Args:
        chat_id (int): Telegram chat ID.
        text (str): Input text
        state (FSMContext): FSM state.
    """
    logger.debug("Starting date processing for user %s: %s", chat_id, text)
    state_data = await state.get_data()
    logger.debug("Current FSM state: %s", state_data)

    try:
        date_obj = datetime.strptime(text, "%d.%m.%Y").date()
        if date_obj < datetime.today().date():
            await bot.send_message(chat_id, "⛔ Date cannot be in the past. Enter again (DD.MM.YYYY):")
            logger.warning("User %s entered a past date: %s", chat_id, text)
            return

        # Save date directly to state
        await state.update_data(step="time", date=date_obj)
        await bot.send_message(chat_id, "⏰ Enter the time (HH:MM):")
        logger.info("Date processed and saved for user %s: %s", chat_id, date_obj)

        # Validate date saving
        updated_state = await state.get_data()
        logger.debug("State after saving date: %s", updated_state)

    except ValueError:
        await bot.send_message(chat_id, "❌ Invalid date format. Enter again (DD.MM.YYYY):")
        logger.warning("Invalid date format from user %s: %s", chat_id, text)
        await state.update_data(step="date")


async def process_time(chat_id: int, text: str, state: FSMContext) -> None:
    """Processes time input for booking.

    Args:
        chat_id (int): Telegram chat ID.
        text (str): Input text
        state (FSMContext): FSM state.
    """
    state_data = await state.get_data()
    logger.debug("FSM state before processing time: %s", state_data)
    date_obj = state_data.get("date")

    if not date_obj:
        await bot.send_message(chat_id, "⛔ Date not specified. Enter the date (DD.MM.YYYY):")
        await state.update_data(step="date")
        logger.warning("Missing date in FSM state for user %s", chat_id)
        return

    try:
        time_obj = datetime.strptime(text, "%H:%M").time()
        now = datetime.now()
        meeting_datetime = datetime.combine(date_obj, time_obj)
        if date_obj == now.date() and meeting_datetime < now:
            await bot.send_message(
                chat_id,
                f"⛔ Time must not be earlier than {now.strftime('%H:%M')}. Enter again (HH:MM):",
            )
            logger.warning("User %s entered a past time: %s", chat_id, text)
            return

        # Save time directly to state
        await state.update_data(step="topic", time=time_obj)
        await bot.send_message(chat_id, "📝 Enter the topic:")
        logger.info("Time processed and saved for user %s: %s", chat_id, time_obj)

        # Validate time saving
        updated_state = await state.get_data()
        logger.debug("State after saving time: %s", updated_state)

    except ValueError:
        await bot.send_message(chat_id, "❌ Invalid time format. Enter again (HH:MM):")
        logger.warning("Invalid time format from user %s: %s", chat_id, text)
        await state.update_data(step="time")


async def process_topic(chat_id: int, text: str, state: FSMContext) -> None:
    """Processes topic input for booking.

    Args:
        chat_id (int): Telegram chat ID.
        text (str): Input text
        state (FSMContext): FSM state.
    """
    logger.debug("Processing topic for user %s: %s", chat_id, text)
    await state.update_data(step="duration", topic=text)
    await bot.send_message(chat_id, "⏳ Enter the duration (30–240 minutes):")
    logger.info("Topic processed and saved for user %s: %s", chat_id, text)
    updated_state = await state.get_data()
    logger.debug("State after saving topic: %s", updated_state)


async def process_duration(chat_id: int, text: str, state: FSMContext) -> None:
    """Processes duration input and books the meeting.

    Args:
        chat_id (int): Telegram chat ID.
        text (str): Input text
        state (FSMContext): FSM state.
    """
    state_data = await state.get_data()
    logger.debug("FSM state before booking: %s", state_data)
    date_obj = state_data.get("date")
    time_obj = state_data.get("time")
    topic = state_data.get("topic")

    if not all([date_obj, time_obj, topic]):
        await bot.send_message(chat_id, "⛔ Not all data provided. Start over with /book.")
        await state.clear()
        logger.warning("Insufficient data for booking for user %s", chat_id)
        return

    try:
        duration = int(text)
        if duration < 30 or duration > 240:
            await bot.send_message(
                chat_id,
                "⛔ Duration must be between 30 and 240 minutes. Enter again:"
            )
            logger.warning("Invalid duration from user %s: %s", chat_id, text)
            return

        start_time = datetime.combine(date_obj, time_obj)
        start_time = timezone.localize(start_time).astimezone(pytz.UTC)
        meeting_data = {
            "topic": topic,
            "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": duration,
        }

        await bot.send_message(chat_id, "🚨 Checking slots...")
        logger.info("Booking meeting for user %s: %s", chat_id, meeting_data)
        meeting_info, alternative_slots = zoom_manager.book_meeting(meeting_data, date_obj)

        if meeting_info:
            link = meeting_info.get("join_url")
            account = meeting_info.get("host_email")
            save_data = {
                "date": date_obj.strftime("%d.%m.%Y"),
                "time": time_obj.strftime("%H:%M"),
                "topic": topic,
                "duration": duration,
                "account": account,
                "link": link,
            }
            success_message = (
                f"✅ Meeting created:\n"
                f"📅 {save_data['date']}\n"
                f"⏰ {save_data['time']}\n"
                f"📝 {save_data['topic']}\n"
                f"⏳ {duration} minutes\n"
                f"👤 Account: {account}\n"
                f"🔗 {link}"
            )
            await bot.send_message(chat_id, success_message)
            db.save_meeting(chat_id, save_data)
            logger.info("Meeting booked for user %s with account %s", chat_id, account)
        else:
            error_details = zoom_manager.get_last_error()
            response = f"⛔ Booking error.\nDetails: {error_details or 'No free slots.'}"
            if alternative_slots:
                response += "\n\n📅 Available slots:\n" + "\n".join(alternative_slots)
                response += "\nChoose a time via /book."
            await bot.send_message(chat_id, response)
            logger.warning("Booking error for user %s: %s", chat_id, error_details)

        await state.clear()

    except ValueError:
        await bot.send_message(chat_id, "❌ Invalid duration format. Enter again:")
        logger.warning("Invalid duration format from user %s: %s", chat_id, text)
        await state.update_data(step="duration")


@router.message(BotStates.booking)
async def process_booking(message: Message, state: FSMContext) -> None:
    """Processes the steps of the meeting booking process.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    chat_id = message.chat.id
    text = message.text.strip()
    state_data = await state.get_data()
    step = state_data.get("step")

    if text == "/cancel":
        await cancel_operation(message, state)
        return

    if step == "date":
        await process_date(chat_id, text, state)
    elif step == "time":
        await process_time(chat_id, text, state)
    elif step == "topic":
        await process_topic(chat_id, text, state)
    elif step == "duration":
        await process_duration(chat_id, text, state)


@router.message(Command("my_meetings"))
async def cmd_my_meetings(message: Message, state: FSMContext) -> None:
    """Shows the user’s meetings.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    chat_id = message.chat.id
    user_id = str(chat_id)
    meetings = db.load_meetings()

    if user_id not in meetings or not meetings[user_id]:
        await bot.send_message(chat_id, "❌ You have no meetings.")
        logger.info("No meetings found for user %s", chat_id)
        await state.clear()
        return

    response = "📅 *Your meetings:*\n\n"
    for meeting in meetings[user_id]:
        response += (
            f"📆 {meeting['date']}\n"
            f"⏰ {meeting['time']}\n"
            f"📝 {meeting['topic']}\n"
            f"👤 Account: {meeting['account']}\n"
            f"⏳ {meeting['duration']} minutes\n"
            f"🔗 {meeting['link']}\n\n"
        )

    await bot.send_message(chat_id, response, parse_mode="Markdown")
    await state.clear()
    logger.info("Displayed %d meetings for user %s", len(meetings[user_id]), chat_id)


@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext) -> None:
    """Starts the meeting deletion process.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    await state.set_state(BotStates.deleting)
    await bot.send_message(message.chat.id, "🔗 Enter the meeting URL to delete:")
    logger.info("Request for meeting URL to delete from user %s", message.chat.id)


@router.message(BotStates.deleting)
async def process_delete(message: Message, state: FSMContext) -> None:
    """Deletes a meeting by URL.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    chat_id = message.chat.id
    meeting_url = message.text.strip()

    if meeting_url == "/cancel":
        await cancel_operation(message, state)
        return

    account = zoom_manager.delete_meeting(meeting_url)
    if account:
        db.remove_meeting_by_url(meeting_url)
        await bot.send_message(chat_id, f"✅ Meeting {meeting_url} deleted (account: {account}).")
        logger.info("Meeting %s deleted for user %s from account %s", meeting_url, chat_id, account)
    else:
        error_details = zoom_manager.get_last_error()
        await bot.send_message(
            chat_id,
            f"⛔ Deletion error.\nDetails: {error_details or 'Meeting not found.'}"
        )
        logger.warning("Error deleting meeting %s for user %s: %s", meeting_url, chat_id, error_details)

    await state.clear()


@router.message(Command("upload_to_youtube"))
async def cmd_upload(message: Message, state: FSMContext) -> None:
    """Starts the process of uploading a recording to YouTube.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    await state.set_state(BotStates.uploading)
    await state.update_data(step="url")
    await bot.send_message(message.chat.id, "🔗 Enter the meeting URL to upload:")
    logger.info("Request for meeting URL to upload from user %s", message.chat.id)


@router.message(BotStates.uploading)
async def process_upload(message: Message, state: FSMContext) -> None:
    """Processes the steps of uploading a recording to YouTube.

    Args:
        message (Message): Incoming Telegram message.
        state (FSMContext): FSM state.
    """
    chat_id = message.chat.id
    text = message.text.strip()
    state_data = await state.get_data()
    step = state_data.get("step")

    if text == "/cancel":
        await cancel_operation(message, state)
        return

    if step == "url":
        await bot.send_message(chat_id, "⏳ Checking recording...")
        logger.info("Processing recording URL %s for user %s", text, chat_id)

        account_email = db.get_email(text)
        title = None
        if account_email:
            logger.info("Meeting found in database for account: %s", account_email)
            title = zoom_manager.download_recording(text, specific_account=account_email)
        else:
            logger.info("Meeting not found in database, checking all accounts")
            title = zoom_manager.download_recording(text)

        if not title:
            error_details = zoom_manager.get_last_error()
            await bot.send_message(
                chat_id,
                f"⚠ Download error.\nDetails: {error_details or 'Recording unavailable.'}"
            )
            logger.warning("Error downloading recording %s for user %s: %s", text, chat_id, error_details)
            return

        zoom_manager.delete_meeting(text)
        db.remove_meeting_by_url(text)
        await state.update_data(step="description", title=title)
        await bot.send_message(chat_id, "📝 Enter description or a dot (.) for empty one:")
        logger.info("Requesting video description for user %s, title: %s", chat_id, title)

    elif step == "description":
        description = None if text == "." else text
        video_path = f"{state_data['title']}.mp4"
        docx_path = f"{state_data['title']}_summary.docx"

        await bot.send_message(chat_id, "⏳ Uploading to YouTube...")
        logger.info("Uploading video to YouTube for user %s: %s", chat_id, state_data["title"])
        link = youtube_manager.upload_video(state_data["title"], description)

        if link:
            await bot.send_message(chat_id, f"✅ Video uploaded: {link}")
            logger.info("Video uploaded for user %s: %s", chat_id, link)
        else:
            error_details = youtube_manager.get_last_error()
            await bot.send_message(
                chat_id,
                f"⛔ Upload error.\nDetails: {error_details}\n"
                f"Files saved: {state_data['title']}.mp4, "
                f"{state_data['title']}_summary.docx"
            )
            logger.warning("Error uploading to YouTube for user %s: %s", chat_id, error_details)

        await state.clear()
        asyncio.create_task(postprocess_files(chat_id, docx_path, video_path))


async def postprocess_files(chat_id: int, docx_path: str, video_path: str) -> None:
    """Sends the summary and deletes local files.

    Args:
        chat_id (int): Telegram chat ID.
        docx_path (str): Path to summary document.
        video_path (str): Path to video file.
    """
    logger.info("Processing files for user %s", chat_id)
    try:
        if os.path.exists(docx_path):
            await bot.send_document(chat_id, FSInputFile(docx_path))
            logger.info("Document %s sent to user %s", docx_path, chat_id)
        else:
            await bot.send_message(chat_id, "⚠ Summary not found.")
            logger.warning("Summary document not found: %s", docx_path)

        for path in [docx_path, video_path]:
            if os.path.exists(path):
                os.remove(path)
                logger.info("File deleted: %s", path)
    except OSError as error:
        logger.error("Error processing files for user %s: %s", chat_id, error)
        await bot.send_message(chat_id, f"⛔ File processing error: {str(error)}")


async def main() -> None:
    """Starts the Telegram bot."""
    logger.info("Starting Telegram bot")
    try:
        await dp.start_polling(bot)
    except Exception as error:
        logger.error("Bot operation error: %s", error)
        raise


if __name__ == "__main__":
    asyncio.run(main())
