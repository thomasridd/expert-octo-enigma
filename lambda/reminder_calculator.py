"""
Reminder interval calculation logic for Leaving Timer Skill
"""

from typing import List


def calculate_reminder_intervals(total_minutes: int) -> List[float]:
    """
    Calculate reminder intervals for a timer based on total duration.

    Rules:
    - For timers >= 60 minutes: Add reminders at each hour boundary and 30-minute mark
    - Always include (if within timer duration): 45, 30, 15, 10, 5, 3, 2, 1 minute, 30 seconds
    - Return as minutes before end (30 seconds = 0.5)
    - Sort descending (furthest first)
    - Remove duplicates

    Args:
        total_minutes: Total timer duration in minutes

    Returns:
        List of reminder intervals in minutes before end, sorted descending

    Examples:
        >>> calculate_reminder_intervals(20)
        [15, 10, 5, 3, 2, 1, 0.5]
        >>> calculate_reminder_intervals(90)
        [90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]
        >>> calculate_reminder_intervals(150)
        [150, 120, 90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]
    """
    intervals = set()

    # Standard intervals (always include if within duration)
    standard_intervals = [45, 30, 15, 10, 5, 3, 2, 1, 0.5]
    for interval in standard_intervals:
        if interval <= total_minutes:
            intervals.add(interval)

    # For timers >= 60 minutes, add hour boundaries and 30-minute marks
    if total_minutes >= 60:
        # Add hour boundaries
        hours = int(total_minutes // 60)
        for h in range(1, hours + 1):
            intervals.add(float(h * 60))

        # Add 30-minute marks between hours
        for h in range(hours):
            half_hour = (h * 60) + 30
            if half_hour <= total_minutes:
                intervals.add(float(half_hour))

    # Sort descending (furthest first)
    sorted_intervals = sorted(intervals, reverse=True)

    return sorted_intervals


def parse_duration_to_minutes(duration_str: str) -> int:
    """
    Convert ISO 8601 duration (PT2H30M) to total minutes.

    Supports formats like:
    - PT30M (30 minutes)
    - PT2H (2 hours = 120 minutes)
    - PT2H30M (2 hours 30 minutes = 150 minutes)
    - PT1H45M (1 hour 45 minutes = 105 minutes)

    Args:
        duration_str: ISO 8601 duration string

    Returns:
        Total duration in minutes

    Raises:
        ValueError: If duration format is invalid
    """
    if not duration_str or not duration_str.startswith('PT'):
        raise ValueError(f"Invalid duration format: {duration_str}")

    # Remove 'PT' prefix
    duration_str = duration_str[2:]

    hours = 0
    minutes = 0

    # Parse hours
    if 'H' in duration_str:
        h_index = duration_str.index('H')
        hours = int(duration_str[:h_index])
        duration_str = duration_str[h_index + 1:]

    # Parse minutes
    if 'M' in duration_str:
        m_index = duration_str.index('M')
        minutes = int(duration_str[:m_index])

    return (hours * 60) + minutes


def format_duration_friendly(minutes: int) -> str:
    """
    Convert minutes to friendly spoken format.

    Examples:
        >>> format_duration_friendly(30)
        '30 minutes'
        >>> format_duration_friendly(90)
        '1 hour and 30 minutes'
        >>> format_duration_friendly(120)
        '2 hours'
        >>> format_duration_friendly(1)
        '1 minute'

    Args:
        minutes: Duration in minutes

    Returns:
        Friendly formatted duration string
    """
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    hours_str = f"{hours} hour{'s' if hours != 1 else ''}"

    if remaining_minutes == 0:
        return hours_str

    minutes_str = f"{remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
    return f"{hours_str} and {minutes_str}"


def generate_reminder_text(minutes_before_end: float) -> str:
    """
    Generate spoken text for reminder based on interval.

    Args:
        minutes_before_end: Minutes before timer ends (0.5 for 30 seconds)

    Returns:
        Spoken text for the reminder
    """
    if minutes_before_end == 0.5:
        return "30 seconds until you need to leave"
    elif minutes_before_end == 0:
        return "It's time to leave now"
    elif minutes_before_end == 1:
        return "1 minute until you need to leave"
    else:
        mins = int(minutes_before_end)
        return f"{mins} minutes until you need to leave"
