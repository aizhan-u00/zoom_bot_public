"""
Module for managing the YouTube API to upload Zoom meeting recordings.


Provides the `YouTubeManager` class for authentication and video uploads to YouTube using 
the YouTube Data API v3. Supports OAuth 2.0, token refresh, and resumable video uploads.
"""
import os
from typing import Optional
import requests
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from logger import logger
from config import YOUTUBE_CREDENTIALS_FILE

class YouTubeManager:
    """Manages interactions with the YouTube API for video uploads."""

    def __init__(self, credentials_file: str = YOUTUBE_CREDENTIALS_FILE):
        """Initializes the YouTube API client.

        Args:
            credentials_file (str): Path to file client_secrets for YouTube API.
                Default is YOUTUBE_CREDENTIALS_FILE from config.
        """
        self.credentials_file = credentials_file
        self.credentials = None
        self.youtube = None
        self.last_error: Optional[str] = None
        self._authenticate()
        logger.info("YouTubeManager initialized")

    def _authenticate(self) -> None:
        """Authenticates with the YouTube API via OAuth 2.0."""
        logger.info("Authenticating with YouTube API")
        try:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                self.credentials_file,
                scopes=[
                    "https://www.googleapis.com/auth/youtube.upload",
                    "https://www.googleapis.com/auth/youtube.readonly"
                ]
            )
            self.credentials = flow.run_local_server(
                port=8080,
                access_type="offline",
                prompt="consent"
            )
            self.youtube = build("youtube", "v3", credentials=self.credentials)
            logger.debug("Authentication successful: client_id=%s", self.credentials.client_id)
        except (OSError, ValueError) as error:
            self.last_error = f"Authentication error: {str(error)}"
            logger.error(self.last_error)
            raise

    def refresh_access_token(self) -> bool:
        """Refreshes the OAuth access token.

        Returns:
            bool: True, if token is refreshed, False in case of error.
        """
        self.last_error = None
        logger.info("Refreshing YouTube access token")
        try:
            url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "refresh_token": self.credentials.refresh_token,
                "grant_type": "refresh_token"
            }
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            response_data = response.json()

            if "access_token" in response_data:
                self.credentials.token = response_data["access_token"]
                self.youtube = build("youtube", "v3", credentials=self.credentials)
                logger.info("Access token successfully refreshed")
                return True

            self.last_error = f"Error refreshing access token: {response_data}"
            logger.error(self.last_error)
            return False
        except requests.RequestException as error:
            self.last_error = f"Token refresh error: {str(error)}"
            logger.error(self.last_error)
            return False

    def get_last_error(self) -> Optional[str]:
        """Returns the last error message.

        Returns:
            Optional[str]: Last error message or None.
        """
        return self.last_error

    def upload_video(self, title: str, description: str = '') -> Optional[str]:
        """Uploads a video to YouTube as unlisted.

        Args:
            title (str): Video title (used for lookup op .mp4 file).
            description (str): Video description. Default is empty string.

        Returns:
            Optional[str]: Youtube URL in  case of successful upload, otherwise None.
        """
        self.last_error = None
        logger.info("Uploading video to YouTube: %s", title)
        video_path = f"{title}.mp4"

        if not os.path.exists(video_path):
            self.last_error = f"Video file not found: {video_path}"
            logger.error(self.last_error)
            return None

        if not self.refresh_access_token():
            return None

        try:
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["Zoom", "Meeting", "Recording"],
                    "categoryId": "27"  # Category "Education"
                },
                "status": {
                    "privacyStatus": "unlisted",
                    "madeForKids": False
                }
            }

            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info("Upload progress: %d%%", int(status.progress() * 100))

            video_id = response.get('id')
            link = f"https://www.youtube.com/watch?v={video_id}"
            logger.info("Video successfully uploaded: %s", link)
            return link

        except HttpError as error:
            self.last_error = f"Video upload error: {str(error)}"
            logger.error(self.last_error)
            return None
