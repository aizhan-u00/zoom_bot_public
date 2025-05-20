# Zoom Meeting Management Bot

## Overview
This project is a Telegram bot designed to manage Zoom meetings and upload recordings to YouTube. It allows users to book, view, delete, and upload Zoom meeting recordings, integrating with the Zoom API, YouTube Data API v3, and a SQLite database for persistent storage. The bot supports multiple Zoom accounts, checks for availability, suggests alternative time slots, and handles meeting summaries in Word documents.

## Features
- **Meeting Booking**: Users can schedule Zoom meetings by providing date, time, topic, and duration.
- **Meeting Management**: View user-specific meetings, and delete meetings by URL.
- **Recording Upload**: Download Zoom meeting recordings and upload them to YouTube as unlisted videos.
- **Summary Generation**: Download Zoom meeting summaries and send as Word documents.
- **Multi-Account Support**: Manages multiple Zoom accounts for scheduling and recording access.
- **Error Handling**: Provides detailed error messages for failed operations.
- **Logging**: Logs all operations to a file (`zoom-bot.log`) and console for debugging and monitoring.

## Project Structure
- **`zoom_bot.py`**: Main bot logic, handles user commands and finite state machine (FSM) for booking and uploading processes.
- **`zoom_manager.py`**: Interacts with the Zoom API for creating, checking, deleting, and downloading meeting recordings.
- **`youtube_manager.py`**: Manages YouTube API interactions for uploading videos.
- **`database.py`**: Manages SQLite database for storing meeting details.
- **`logger.py`**: Configures logging for the application.
- **`config.py`**: Contains configuration settings for the bot, Zoom, and YouTube APIs.
- **`requirements.txt`**: Lists required Python packages.

## Requirements
- Python 3.8+
- Libraries listed in `requirements.txt`:
  - `requests`
  - `pytz`
  - `aiogram`
  - `asyncio`
  - `google-auth`
  - `google-auth-oauthlib`
  - `google-api-python-client`
  - `python-dateutil`
  - `python-docx`

## Setup
1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Bot**:
   - Edit `config.py` to include:
     - `BOT_TOKEN`: Telegram bot token from BotFather.
     - `ZOOM_ACCOUNTS`: List of dictionaries with Zoom account details (`email`, `client_id`, `client_secret`).
     - `ZOOM_API_BASE`: Zoom API base URL (default: `https://api.zoom.us/v2`).
     - `YOUTUBE_CREDENTIALS_FILE`: Path to the YouTube API `client_secrets.json` file (obtain from Google Cloud Console).
     - `TIMEZONE`: Timezone for scheduling (default: `Asia/Almaty`).
   - Ensure the `client_secrets.json` file for YouTube API is in the project directory.

4. **Set Up YouTube API**:
   - Create a project in the Google Cloud Console.
   - Enable the YouTube Data API v3.
   - Generate OAuth 2.0 credentials and download the `client_secrets.json` file.
   - Place the file in the project directory as specified in `YOUTUBE_CREDENTIALS_FILE`.

5. **Run the Bot**:
   ```bash
   python zoom_bot.py
   ```

## Usage
- **User Commands**:
  - `/start` or `/help`: Displays a welcome message with available commands.
  - `/book`: Starts the booking process (date, time, topic, duration).
  - `/my_meetings`: Shows the user’s scheduled meetings.
  - `/delete`: Deletes a meeting by its Zoom URL.
  - `/upload_to_youtube`: Downloads a Zoom recording and uploads it to YouTube.
  - `/cancel`: Cancels the current operation.

- **Booking Process**:
  - Users provide date (DD.MM.YYYY), time (HH:MM), topic, and duration (30–240 minutes).
  - The bot checks Zoom account availability and books the meeting or suggests alternative slots.
  - Meeting details are saved to the SQLite database and sent to the user.

- **Recording Upload**:
  - Users provide the meeting URL to download the recording.
  - The bot downloads the recording and its summary, uploads the video to YouTube as unlisted, and sends the summary as a Word document.
  - Local files are deleted after processing.

- **Error Handling**:
  - The bot provides detailed error messages for failed operations (e.g., invalid input, API errors).
  - Logs are saved to `zoom-bot.log` (DEBUG level) and printed to the console (INFO level).

## Configuration Notes
- **Sensitive Data**: Store `BOT_TOKEN`, `ZOOM_ACCOUNTS`, and YouTube credentials securely.
- **Timezone**: Ensure `TIMEZONE` in `config.py` matches your desired timezone (e.g., `Asia/Almaty` for GMT+5).
- **Zoom Accounts**: Add multiple accounts to `ZOOM_ACCOUNTS` for load balancing and availability.
- **Logging**: Logs are saved to `zoom-bot.log` and printed to the console for monitoring.

## Development
- **Adding Features**:
  - Modify `zoom_bot.py` for new bot commands or FSM states.
  - Extend `zoom_manager.py` for additional Zoom API endpoints.
  - Update `youtube_manager.py` for enhanced YouTube functionality.
  - Adjust `database.py` for new database tables or queries.
- **Testing**:
  - Test booking with valid and invalid inputs.
  - Verify meeting deletion and recording uploads.
  - Check database operations and file handling.

## Troubleshooting
- **Bot Not Responding**: Ensure `BOT_TOKEN` is correct and the bot is running.
- **Zoom API Errors**: Verify `ZOOM_ACCOUNTS` credentials and `ZOOM_API_BASE`.
- **YouTube API Errors**: Check `client_secrets.json` and OAuth authentication.
- **Database Issues**: Ensure `meetings.db` is writable and initialized.
- **Logs**: Review `zoom-bot.log` for detailed error messages.
