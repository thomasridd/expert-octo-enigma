"""
Unit tests for timer_storage module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from lambda.timer_storage import (
    TimerData,
    create_timer,
    get_active_timer,
    delete_timer,
    update_timer_reminders
)


class TestTimerData(unittest.TestCase):
    """Test cases for TimerData class"""

    def test_to_dict(self):
        """Test converting TimerData to dictionary"""
        timer = TimerData(
            user_id='user123',
            timer_id='timer456',
            start_time='2024-01-15T14:00:00Z',
            end_time='2024-01-15T16:00:00Z',
            duration_minutes=120,
            reminder_ids=['rem1', 'rem2'],
            expires_at=1705334400
        )

        result = timer.to_dict()

        self.assertEqual(result['userId'], 'user123')
        self.assertEqual(result['timerId'], 'timer456')
        self.assertEqual(result['startTime'], '2024-01-15T14:00:00Z')
        self.assertEqual(result['endTime'], '2024-01-15T16:00:00Z')
        self.assertEqual(result['durationMinutes'], 120)
        self.assertEqual(result['reminderIds'], ['rem1', 'rem2'])
        self.assertEqual(result['expiresAt'], 1705334400)

    def test_from_dict(self):
        """Test creating TimerData from dictionary"""
        data = {
            'userId': 'user123',
            'timerId': 'timer456',
            'startTime': '2024-01-15T14:00:00Z',
            'endTime': '2024-01-15T16:00:00Z',
            'durationMinutes': 120,
            'reminderIds': ['rem1', 'rem2'],
            'expiresAt': 1705334400
        }

        timer = TimerData.from_dict(data)

        self.assertEqual(timer.user_id, 'user123')
        self.assertEqual(timer.timer_id, 'timer456')
        self.assertEqual(timer.start_time, '2024-01-15T14:00:00Z')
        self.assertEqual(timer.end_time, '2024-01-15T16:00:00Z')
        self.assertEqual(timer.duration_minutes, 120)
        self.assertEqual(timer.reminder_ids, ['rem1', 'rem2'])
        self.assertEqual(timer.expires_at, 1705334400)

    def test_from_dict_missing_reminder_ids(self):
        """Test creating TimerData from dict without reminder_ids"""
        data = {
            'userId': 'user123',
            'timerId': 'timer456',
            'startTime': '2024-01-15T14:00:00Z',
            'endTime': '2024-01-15T16:00:00Z',
            'durationMinutes': 120,
            'expiresAt': 1705334400
        }

        timer = TimerData.from_dict(data)
        self.assertEqual(timer.reminder_ids, [])


class TestCreateTimer(unittest.TestCase):
    """Test cases for create_timer function"""

    @patch('lambda.timer_storage.table')
    def test_create_timer_success(self, mock_table):
        """Test successful timer creation"""
        mock_table.put_item = Mock()

        result = create_timer(
            user_id='user123',
            duration_minutes=60,
            reminder_ids=['rem1', 'rem2', 'rem3']
        )

        # Verify put_item was called
        mock_table.put_item.assert_called_once()

        # Verify result
        self.assertIsInstance(result, TimerData)
        self.assertEqual(result.user_id, 'user123')
        self.assertEqual(result.duration_minutes, 60)
        self.assertEqual(result.reminder_ids, ['rem1', 'rem2', 'rem3'])
        self.assertIsNotNone(result.timer_id)
        self.assertIsNotNone(result.start_time)
        self.assertIsNotNone(result.end_time)
        self.assertIsNotNone(result.expires_at)

    @patch('lambda.timer_storage.table')
    def test_create_timer_dynamodb_error(self, mock_table):
        """Test timer creation with DynamoDB error"""
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'PutItem'
        )

        with self.assertRaises(ClientError):
            create_timer(
                user_id='user123',
                duration_minutes=60,
                reminder_ids=['rem1']
            )


class TestGetActiveTimer(unittest.TestCase):
    """Test cases for get_active_timer function"""

    @patch('lambda.timer_storage.table')
    def test_get_timer_exists(self, mock_table):
        """Test getting an existing active timer"""
        # Create a timer that ends in the future
        future_time = datetime.utcnow() + timedelta(minutes=30)

        mock_table.get_item.return_value = {
            'Item': {
                'userId': 'user123',
                'timerId': 'timer456',
                'startTime': '2024-01-15T14:00:00Z',
                'endTime': future_time.isoformat() + 'Z',
                'durationMinutes': 60,
                'reminderIds': ['rem1', 'rem2'],
                'expiresAt': int(future_time.timestamp())
            }
        }

        result = get_active_timer('user123')

        # Verify get_item was called
        mock_table.get_item.assert_called_once_with(Key={'userId': 'user123'})

        # Verify result
        self.assertIsInstance(result, TimerData)
        self.assertEqual(result.user_id, 'user123')
        self.assertEqual(result.timer_id, 'timer456')

    @patch('lambda.timer_storage.table')
    def test_get_timer_not_found(self, mock_table):
        """Test getting a timer that doesn't exist"""
        mock_table.get_item.return_value = {}

        result = get_active_timer('user123')

        self.assertIsNone(result)

    @patch('lambda.timer_storage.delete_timer')
    @patch('lambda.timer_storage.table')
    def test_get_timer_expired(self, mock_table, mock_delete):
        """Test getting an expired timer"""
        # Create a timer that ended in the past
        past_time = datetime.utcnow() - timedelta(minutes=30)

        mock_table.get_item.return_value = {
            'Item': {
                'userId': 'user123',
                'timerId': 'timer456',
                'startTime': '2024-01-15T14:00:00Z',
                'endTime': past_time.isoformat() + 'Z',
                'durationMinutes': 60,
                'reminderIds': ['rem1', 'rem2'],
                'expiresAt': int(past_time.timestamp())
            }
        }

        result = get_active_timer('user123')

        # Should delete the expired timer
        mock_delete.assert_called_once_with('user123')
        self.assertIsNone(result)

    @patch('lambda.timer_storage.table')
    def test_get_timer_dynamodb_error(self, mock_table):
        """Test get_active_timer with DynamoDB error"""
        mock_table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'GetItem'
        )

        with self.assertRaises(ClientError):
            get_active_timer('user123')


class TestDeleteTimer(unittest.TestCase):
    """Test cases for delete_timer function"""

    @patch('lambda.timer_storage.table')
    def test_delete_timer_success(self, mock_table):
        """Test successful timer deletion"""
        mock_table.delete_item.return_value = {
            'Attributes': {
                'userId': 'user123',
                'timerId': 'timer456'
            }
        }

        result = delete_timer('user123')

        mock_table.delete_item.assert_called_once()
        self.assertTrue(result)

    @patch('lambda.timer_storage.table')
    def test_delete_timer_not_found(self, mock_table):
        """Test deleting a timer that doesn't exist"""
        mock_table.delete_item.return_value = {}

        result = delete_timer('user123')

        self.assertFalse(result)

    @patch('lambda.timer_storage.table')
    def test_delete_timer_dynamodb_error(self, mock_table):
        """Test delete_timer with DynamoDB error"""
        mock_table.delete_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'DeleteItem'
        )

        with self.assertRaises(ClientError):
            delete_timer('user123')


class TestUpdateTimerReminders(unittest.TestCase):
    """Test cases for update_timer_reminders function"""

    @patch('lambda.timer_storage.table')
    def test_update_reminders_success(self, mock_table):
        """Test successful reminder update"""
        mock_table.update_item.return_value = {
            'Attributes': {
                'userId': 'user123',
                'reminderIds': ['new1', 'new2']
            }
        }

        result = update_timer_reminders('user123', ['new1', 'new2'])

        mock_table.update_item.assert_called_once()
        self.assertTrue(result)

    @patch('lambda.timer_storage.table')
    def test_update_reminders_not_found(self, mock_table):
        """Test updating reminders for non-existent timer"""
        mock_table.update_item.return_value = {}

        result = update_timer_reminders('user123', ['new1', 'new2'])

        self.assertFalse(result)

    @patch('lambda.timer_storage.table')
    def test_update_reminders_dynamodb_error(self, mock_table):
        """Test update_timer_reminders with DynamoDB error"""
        mock_table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'UpdateItem'
        )

        with self.assertRaises(ClientError):
            update_timer_reminders('user123', ['new1', 'new2'])


if __name__ == '__main__':
    unittest.main()
