"""
DynamoDB operations for Leaving Timer storage
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'LeavingTimerData')
table = dynamodb.Table(table_name)


class TimerData:
    """Data class for timer information"""

    def __init__(
        self,
        user_id: str,
        timer_id: str,
        start_time: str,
        end_time: str,
        duration_minutes: int,
        reminder_ids: List[str],
        expires_at: int
    ):
        self.user_id = user_id
        self.timer_id = timer_id
        self.start_time = start_time
        self.end_time = end_time
        self.duration_minutes = duration_minutes
        self.reminder_ids = reminder_ids
        self.expires_at = expires_at

    def to_dict(self) -> Dict:
        """Convert to DynamoDB item format"""
        return {
            'userId': self.user_id,
            'timerId': self.timer_id,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'durationMinutes': self.duration_minutes,
            'reminderIds': self.reminder_ids,
            'expiresAt': self.expires_at
        }

    @staticmethod
    def from_dict(data: Dict) -> 'TimerData':
        """Create TimerData from DynamoDB item"""
        return TimerData(
            user_id=data['userId'],
            timer_id=data['timerId'],
            start_time=data['startTime'],
            end_time=data['endTime'],
            duration_minutes=data['durationMinutes'],
            reminder_ids=data.get('reminderIds', []),
            expires_at=data['expiresAt']
        )


def create_timer(
    user_id: str,
    duration_minutes: int,
    reminder_ids: List[str]
) -> TimerData:
    """
    Create a new timer in DynamoDB.

    Args:
        user_id: Alexa user ID
        duration_minutes: Timer duration in minutes
        reminder_ids: List of Alexa reminder IDs

    Returns:
        TimerData object

    Raises:
        ClientError: If DynamoDB operation fails
    """
    try:
        timer_id = str(uuid.uuid4())
        now = datetime.utcnow()
        start_time = now.isoformat() + 'Z'
        end_time = (now + timedelta(minutes=duration_minutes)).isoformat() + 'Z'

        # Set TTL to 1 hour after end time
        expires_at = int((now + timedelta(minutes=duration_minutes, hours=1)).timestamp())

        timer_data = TimerData(
            user_id=user_id,
            timer_id=timer_id,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            reminder_ids=reminder_ids,
            expires_at=expires_at
        )

        table.put_item(Item=timer_data.to_dict())
        logger.info(f"Created timer {timer_id} for user {user_id}")

        return timer_data

    except ClientError as e:
        logger.error(f"Error creating timer: {e}")
        raise


def get_active_timer(user_id: str) -> Optional[TimerData]:
    """
    Retrieve the active timer for a user.

    Args:
        user_id: Alexa user ID

    Returns:
        TimerData if found, None otherwise

    Raises:
        ClientError: If DynamoDB operation fails
    """
    try:
        response = table.get_item(Key={'userId': user_id})

        if 'Item' not in response:
            logger.info(f"No timer found for user {user_id}")
            return None

        timer_data = TimerData.from_dict(response['Item'])

        # Check if timer has expired
        end_time = datetime.fromisoformat(timer_data.end_time.replace('Z', '+00:00'))
        if datetime.utcnow().replace(tzinfo=end_time.tzinfo) > end_time:
            logger.info(f"Timer {timer_data.timer_id} has expired")
            # Timer expired, delete it
            delete_timer(user_id)
            return None

        return timer_data

    except ClientError as e:
        logger.error(f"Error retrieving timer: {e}")
        raise


def delete_timer(user_id: str) -> bool:
    """
    Delete a timer from DynamoDB.

    Args:
        user_id: Alexa user ID

    Returns:
        True if deleted, False if not found

    Raises:
        ClientError: If DynamoDB operation fails
    """
    try:
        response = table.delete_item(
            Key={'userId': user_id},
            ReturnValues='ALL_OLD'
        )

        if 'Attributes' in response:
            logger.info(f"Deleted timer for user {user_id}")
            return True
        else:
            logger.info(f"No timer found to delete for user {user_id}")
            return False

    except ClientError as e:
        logger.error(f"Error deleting timer: {e}")
        raise


def update_timer_reminders(user_id: str, reminder_ids: List[str]) -> bool:
    """
    Update the reminder IDs for an existing timer.

    Args:
        user_id: Alexa user ID
        reminder_ids: List of Alexa reminder IDs

    Returns:
        True if updated, False if not found

    Raises:
        ClientError: If DynamoDB operation fails
    """
    try:
        response = table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET reminderIds = :ids',
            ExpressionAttributeValues={':ids': reminder_ids},
            ReturnValues='ALL_NEW'
        )

        if 'Attributes' in response:
            logger.info(f"Updated reminders for user {user_id}")
            return True
        else:
            logger.info(f"No timer found to update for user {user_id}")
            return False

    except ClientError as e:
        logger.error(f"Error updating timer reminders: {e}")
        raise
