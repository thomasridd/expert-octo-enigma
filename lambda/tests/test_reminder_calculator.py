"""
Unit tests for reminder_calculator module
"""

import unittest
from lambda.reminder_calculator import (
    calculate_reminder_intervals,
    parse_duration_to_minutes,
    format_duration_friendly,
    generate_reminder_text
)


class TestCalculateReminderIntervals(unittest.TestCase):
    """Test cases for calculate_reminder_intervals function"""

    def test_1_minute_timer(self):
        """Test 1 minute timer - only includes intervals <= 1"""
        result = calculate_reminder_intervals(1)
        expected = [1, 0.5]
        self.assertEqual(result, expected)

    def test_5_minute_timer(self):
        """Test 5 minute timer"""
        result = calculate_reminder_intervals(5)
        expected = [5, 3, 2, 1, 0.5]
        self.assertEqual(result, expected)

    def test_20_minute_timer(self):
        """Test 20 minute timer - from README example"""
        result = calculate_reminder_intervals(20)
        expected = [15, 10, 5, 3, 2, 1, 0.5]
        self.assertEqual(result, expected)

    def test_30_minute_timer(self):
        """Test 30 minute timer"""
        result = calculate_reminder_intervals(30)
        expected = [30, 15, 10, 5, 3, 2, 1, 0.5]
        self.assertEqual(result, expected)

    def test_90_minute_timer(self):
        """Test 90 minute timer - from README example"""
        result = calculate_reminder_intervals(90)
        expected = [90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]
        self.assertEqual(result, expected)

    def test_120_minute_timer(self):
        """Test 2 hour timer"""
        result = calculate_reminder_intervals(120)
        expected = [120, 90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]
        self.assertEqual(result, expected)

    def test_150_minute_timer(self):
        """Test 150 minute timer - from README example"""
        result = calculate_reminder_intervals(150)
        expected = [150, 120, 90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]
        self.assertEqual(result, expected)

    def test_300_minute_timer(self):
        """Test 5 hour timer - multiple hour boundaries"""
        result = calculate_reminder_intervals(300)
        # Should have hour marks at 60, 120, 180, 240, 300
        # 30-min marks at 30, 90, 150, 210, 270
        # Standard intervals at 45, 30, 15, 10, 5, 3, 2, 1, 0.5
        expected = [300, 270, 240, 210, 180, 150, 120, 90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]
        self.assertEqual(result, expected)

    def test_no_duplicates(self):
        """Test that duplicates are removed"""
        # 60 minute timer should not have duplicate 30 or 60
        result = calculate_reminder_intervals(60)
        # Check no duplicates
        self.assertEqual(len(result), len(set(result)))

    def test_descending_order(self):
        """Test that intervals are sorted descending"""
        result = calculate_reminder_intervals(150)
        self.assertEqual(result, sorted(result, reverse=True))


class TestParseDurationToMinutes(unittest.TestCase):
    """Test cases for parse_duration_to_minutes function"""

    def test_minutes_only(self):
        """Test parsing minutes only"""
        self.assertEqual(parse_duration_to_minutes('PT30M'), 30)
        self.assertEqual(parse_duration_to_minutes('PT1M'), 1)
        self.assertEqual(parse_duration_to_minutes('PT45M'), 45)

    def test_hours_only(self):
        """Test parsing hours only"""
        self.assertEqual(parse_duration_to_minutes('PT1H'), 60)
        self.assertEqual(parse_duration_to_minutes('PT2H'), 120)
        self.assertEqual(parse_duration_to_minutes('PT5H'), 300)

    def test_hours_and_minutes(self):
        """Test parsing hours and minutes"""
        self.assertEqual(parse_duration_to_minutes('PT1H30M'), 90)
        self.assertEqual(parse_duration_to_minutes('PT2H15M'), 135)
        self.assertEqual(parse_duration_to_minutes('PT2H30M'), 150)

    def test_invalid_format(self):
        """Test that invalid formats raise ValueError"""
        with self.assertRaises(ValueError):
            parse_duration_to_minutes('30M')
        with self.assertRaises(ValueError):
            parse_duration_to_minutes('')
        with self.assertRaises(ValueError):
            parse_duration_to_minutes('invalid')


class TestFormatDurationFriendly(unittest.TestCase):
    """Test cases for format_duration_friendly function"""

    def test_single_minute(self):
        """Test formatting 1 minute"""
        self.assertEqual(format_duration_friendly(1), '1 minute')

    def test_multiple_minutes(self):
        """Test formatting multiple minutes"""
        self.assertEqual(format_duration_friendly(30), '30 minutes')
        self.assertEqual(format_duration_friendly(45), '45 minutes')

    def test_single_hour(self):
        """Test formatting 1 hour"""
        self.assertEqual(format_duration_friendly(60), '1 hour')

    def test_multiple_hours(self):
        """Test formatting multiple hours"""
        self.assertEqual(format_duration_friendly(120), '2 hours')
        self.assertEqual(format_duration_friendly(300), '5 hours')

    def test_hours_and_minutes(self):
        """Test formatting hours and minutes"""
        self.assertEqual(format_duration_friendly(90), '1 hour and 30 minutes')
        self.assertEqual(format_duration_friendly(135), '2 hours and 15 minutes')
        self.assertEqual(format_duration_friendly(150), '2 hours and 30 minutes')

    def test_hours_and_one_minute(self):
        """Test formatting hours and 1 minute (singular)"""
        self.assertEqual(format_duration_friendly(61), '1 hour and 1 minute')
        self.assertEqual(format_duration_friendly(121), '2 hours and 1 minute')


class TestGenerateReminderText(unittest.TestCase):
    """Test cases for generate_reminder_text function"""

    def test_30_seconds(self):
        """Test 30 seconds reminder"""
        self.assertEqual(
            generate_reminder_text(0.5),
            '30 seconds until you need to leave'
        )

    def test_1_minute(self):
        """Test 1 minute reminder"""
        self.assertEqual(
            generate_reminder_text(1),
            '1 minute until you need to leave'
        )

    def test_multiple_minutes(self):
        """Test multiple minutes reminders"""
        self.assertEqual(
            generate_reminder_text(5),
            '5 minutes until you need to leave'
        )
        self.assertEqual(
            generate_reminder_text(15),
            '15 minutes until you need to leave'
        )
        self.assertEqual(
            generate_reminder_text(30),
            '30 minutes until you need to leave'
        )

    def test_zero_minutes(self):
        """Test time to leave now"""
        self.assertEqual(
            generate_reminder_text(0),
            "It's time to leave now"
        )


if __name__ == '__main__':
    unittest.main()
