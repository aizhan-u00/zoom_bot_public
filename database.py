"""
Database module for managing Zoom meeting data using SQLite.

Provides the `DataBase` class for storing and retrieving meeting information, 
including user ID, date, time, topic, duration, account, and URL.
Uses SQLite for reliable and efficient data storage.
"""
import sqlite3
from typing import Dict, List, Optional, Any
from logger import logger

class DataBase:
    """Manages the storage of Zoom meeting data in SQLite."""

    def __init__(self, db_path: str = "meetings.db"):
        """Initializes the database connection and creates the meetings table.

        Args:
            db_path (str): Path to SQLite database file. Default is 'meetings.db'.
        """
        self.db_path = db_path
        self._initialize_database()
        logger.info("Database initialized: %s", db_path)

    def _initialize_database(self) -> None:
        """Creates the meetings table and indexes if they do not exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meetings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL,
                        topic TEXT NOT NULL,
                        duration INTEGER NOT NULL,
                        account TEXT NOT NULL,
                        join_url TEXT NOT NULL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON meetings (user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_join_url ON meetings (join_url)")
                conn.commit()
                logger.debug("Meetings table and indexes created or verified")
        except sqlite3.Error as error:
            logger.error("Database initialization error: %s", error)
            raise

    def save_meeting(self, user_id: int, save_data: Dict[str, Any]) -> None:
        """Saves meeting data for a user.

        Args:
            user_id (int): Telegram user ID.
            save_data (Dict[str, Any]): Meeting data (date, time, topic, duration,
                account, join_url).
        """
        logger.info("Saving meeting for user %s", user_id)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO meetings (user_id, date, time, topic, duration, account, join_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(user_id),
                    save_data["date"],
                    save_data["time"],
                    save_data["topic"],
                    save_data["duration"],
                    save_data["account"],
                    save_data["link"]
                ))
                conn.commit()
                logger.debug("Meeting saved: %s", save_data)
        except sqlite3.Error as error:
            logger.error("Error saving meeting for user %s: %s", user_id, error)
            raise

    def load_meetings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Loads all meetings from the database.

        Returns:
            Dict[str, List[Dict[str, Any]]]: 
                Dictionary with user IDs and meeting lists.
        """
        logger.info("Loading all meetings from database")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM meetings")
                rows = cursor.fetchall()

                meetings: Dict[str, List[Dict[str, Any]]] = {}
                for row in rows:
                    user_id = row["user_id"]
                    meeting = {
                        "date": row["date"],
                        "time": row["time"],
                        "topic": row["topic"],
                        "duration": row["duration"],
                        "account": row["account"],
                        "link": row["join_url"]
                    }
                    if user_id not in meetings:
                        meetings[user_id] = []
                    meetings[user_id].append(meeting)

                logger.debug("Loaded %d meetings", sum(len(m) for m in meetings.values()))
                return meetings
        except sqlite3.Error as error:
            logger.error("Error loading meetings: %s", error)
            return {}

    def get_email(self, join_url: str) -> Optional[str]:
        """Retrieves the account email for a meeting by its join_url.

        Args:
            join_url (str): URL to join the meeting.

        Returns:
            Optional[str]: Account email if found, otherwise None.
        """
        logger.info("Retrieving email for join_url: %s", join_url)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT account FROM meetings WHERE join_url = ?", (join_url,))
                row = cursor.fetchone()
                if row:
                    logger.debug("Found account email: %s", row["account"])
                    return row["account"]
                logger.info("Account email not found for join_url: %s", join_url)
                return None
        except sqlite3.Error as error:
            logger.error("Error retrieving account email: %s", error)
            return None

    def remove_meeting_by_url(self, join_url: str) -> bool:
        """Deletes a meeting by its join_url.

        Args:
            join_url (str): URL to join the meeting.

        Returns:
            bool: True, if meeting was deleted, False, if not found.
        """
        logger.info("Deleting meeting by join_url: %s", join_url)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM meetings WHERE join_url = ?", (join_url,))
                conn.commit()
                if cursor.rowcount > 0:
                    logger.debug("Meeting successfully deleted")
                    return True
                logger.info("Meeting not found by join_url: %s", join_url)
                return False
        except sqlite3.Error as error:
            logger.error("Error deleting meeting: %s", error)
            return False
