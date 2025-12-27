# Alexa Leaving Timer Skill - Claude Code Specification

## Overview

Build an Alexa skill that creates timers with progressive reminder intervals, designed to help families prepare to leave the house. Uses Alexa Reminders API for native notifications.

## Project Structure

```
leaving-timer-skill/
├── lambda/
│   ├── lambda_function.py          # Main Lambda handler
│   ├── reminder_calculator.py      # Interval calculation logic
│   ├── timer_storage.py            # DynamoDB operations
│   ├── requirements.txt            # Python dependencies
│   └── tests/
│       ├── test_reminder_calculator.py
│       └── test_timer_storage.py
├── skill-package/
│   ├── skill.json                  # Skill manifest
│   └── interactionModels/
│       └── custom/
│           └── en-GB.json          # UK English interaction model
├── infrastructure/
│   └── template.yaml               # AWS SAM/CloudFormation
└── README.md
```

## Requirements

### Dependencies (requirements.txt)

```
ask-sdk-core==1.19.0
ask-sdk-dynamodb-persistence-adapter==1.19.0
boto3==1.28.0
python-dateutil==2.8.2
```

### AWS Resources

- Lambda function (Python 3.11 runtime)
- DynamoDB table: `LeavingTimerData`
  - Partition key: `userId` (String)
  - TTL attribute: `expiresAt` (Number)
- IAM role with permissions:
  - DynamoDB read/write
  - CloudWatch Logs
  - Alexa reminder management (handled by skill permissions)

## Functional Specification

### 1. Reminder Interval Logic

**Function**: `calculate_reminder_intervals(total_minutes: int) -> List[float]`

Rules:

- For timers ≥ 60 minutes: Add reminders at each hour boundary and 30-minute mark
- Always include (if within timer duration): 45, 30, 15, 10, 5, 3, 2, 1 minute, 30 seconds
- Return as minutes before end (30 seconds = 0.5)
- Sort descending (furthest first)
- Remove duplicates

Examples:

- 20 min timer → [15, 10, 5, 3, 2, 1, 0.5]
- 90 min timer → [90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]
- 150 min timer → [150, 120, 90, 60, 45, 30, 15, 10, 5, 3, 2, 1, 0.5]

### 2. Voice Interaction Design

#### Intents

**SetLeavingTimerIntent**

- Utterances:
  - “set a leaving timer for {duration}”
  - “we need to leave in {duration}”
  - “remind me to leave in {duration}”
  - “set a {duration} leaving timer”
- Slot: `duration` (AMAZON.DURATION)
- Permissions required: `alexa::alerts:reminders:skill:readwrite`

**CheckTimerIntent**

- Utterances:
  - “how much time until we leave”
  - “check my leaving timer”
  - “how long do we have”
- No slots

**CancelTimerIntent**

- Utterances:
  - “cancel my leaving timer”
  - “stop the leaving timer”
  - “delete my timer”
- No slots

**AMAZON.HelpIntent** (built-in)
**AMAZON.CancelIntent** (built-in)
**AMAZON.StopIntent** (built-in)

### 3. Data Model

**DynamoDB Schema**

```python
{
    'userId': 'amzn1.ask.account.XXX',  # Partition key
    'timerId': 'uuid-string',
    'startTime': '2024-01-15T14:30:00Z',  # ISO 8601
    'endTime': '2024-01-15T16:30:00Z',
    'durationMinutes': 120,
    'reminderIds': [
        'alexa-reminder-id-1',
        'alexa-reminder-id-2',
        # ... one per interval
    ],
    'expiresAt': 1705334400  # Unix timestamp for TTL (1 hour after endTime)
}
```

### 4. Core Behaviors

#### Setting a Timer

1. Parse duration from slot (handle PT2H, PT90M formats)
1. Check for existing active timer:

- If exists: Ask “You already have a timer. Replace it?”
- Use dialog elicitation

1. Calculate reminder intervals
1. Get user timezone from device settings
1. Create Alexa reminders for each interval:

- Spoken text: “{X} minutes until you need to leave”
- For 30 seconds: “30 seconds until you need to leave”
- For final reminder (0 mins): “It’s time to leave now”

1. Store timer data in DynamoDB
1. Respond: “Timer set for {duration}. I’ll remind you at {count} intervals, starting at {first_interval}.”

#### Checking a Timer

1. Retrieve active timer from DynamoDB
1. Calculate remaining time
1. If no timer: “You don’t have an active leaving timer”
1. If expired: Clean up and respond “Your timer has finished”
1. Respond: “You have {X} minutes and {Y} seconds until you need to leave”

#### Canceling a Timer

1. Retrieve timer from DynamoDB
1. Delete all associated reminders via Alexa API
1. Delete timer record from DynamoDB
1. Respond: “I’ve cancelled your leaving timer and all reminders”

#### Permission Handling

- If reminder permission not granted:
  - Send permission request card to Alexa app
  - Respond: “I need permission to set reminders. I’ve sent a card to your Alexa app. Please enable reminders and try again.”

### 5. Error Handling

**Scenarios to handle:**

- Permission denied → Send permission card, friendly message
- Invalid duration (negative, zero, > 24 hours) → “Please specify a duration between 1 minute and 24 hours”
- DynamoDB errors → Log error, respond “Sorry, I’m having trouble accessing your timers right now”
- Reminder creation fails (hit 100 reminder limit) → “You have too many reminders. Please delete some from your Alexa app”
- Timer already exists → Confirm before overwriting
- Network timeout → Graceful degradation with retry suggestion

### 6. Implementation Requirements

#### Lambda Handler Structure

```python
def lambda_handler(event, context):
    # Initialize skill builder with DynamoDB persistence
    # Register request handlers in priority order:
    # 1. LaunchRequestHandler
    # 2. SetLeavingTimerIntentHandler
    # 3. CheckTimerIntentHandler
    # 4. CancelTimerIntentHandler
    # 5. HelpIntentHandler
    # 6. CancelAndStopIntentHandler
    # 7. SessionEndedRequestHandler
    # 8. IntentReflectorHandler (catchall)
    # 9. ErrorHandler
    pass
```

#### Helper Functions Needed

**Duration Parsing**

```python
def parse_duration_to_minutes(duration_str: str) -> int:
    """Convert ISO 8601 duration (PT2H30M) to total minutes"""
    pass
```

**Timezone Handling**

```python
def get_user_timezone(handler_input) -> str:
    """Fetch timezone from device settings API"""
    pass
```

**Friendly Duration Formatting**

```python
def format_duration_friendly(minutes: int) -> str:
    """Convert 150 -> '2 hours and 30 minutes'"""
    pass
```

**Reminder Text Generation**

```python
def generate_reminder_text(minutes_before_end: float) -> str:
    """Generate spoken text for reminder based on interval"""
    pass
```

### 7. Testing Requirements

**Unit Tests**

- `test_reminder_calculator.py`: Test interval calculation for edge cases (1 min, 30 min, 2 hours, 5 hours)
- `test_timer_storage.py`: Mock DynamoDB operations

**Integration Tests**

- Test full flow with mocked Alexa SDK
- Test permission denial scenario
- Test timer replacement flow

**Manual Testing Checklist**

- [ ] Set 30-minute timer, verify 7 reminders created
- [ ] Set 2-hour timer, verify hourly + standard reminders
- [ ] Cancel timer mid-duration, verify reminders deleted
- [ ] Try setting timer without permission, verify card sent
- [ ] Check timer status at various points
- [ ] Set timer, then try to set another (replacement flow)

### 8. Deployment

**Environment Variables**

- `DYNAMODB_TABLE_NAME`: Name of DynamoDB table
- `LOG_LEVEL`: INFO (production) or DEBUG

**SAM Template Requirements**

- Lambda timeout: 10 seconds
- Memory: 256 MB
- Environment: Python 3.11
- Trigger: Alexa Skills Kit
- DynamoDB table with TTL enabled on `expiresAt`

### 9. Skill Manifest (skill.json)

**Key Configuration**

```json
{
  "manifest": {
    "publishingInformation": {
      "locales": {
        "en-GB": {
          "name": "Leaving Timer Helper"
        }
      }
    },
    "permissions": [
      {
        "name": "alexa::alerts:reminders:skill:readwrite"
      }
    ],
    "apis": {
      "custom": {
        "endpoint": {
          "uri": "arn:aws:lambda:eu-west-2:ACCOUNT:function:leaving-timer"
        }
      }
    }
  }
}
```

### 10. Success Criteria

The implementation should:

- ✅ Create reminders at correct intervals for various durations
- ✅ Handle permission flow gracefully
- ✅ Prevent duplicate timers (with user confirmation)
- ✅ Clean up reminders on cancellation
- ✅ Persist timer state across skill invocations
- ✅ Use correct timezone for reminder scheduling
- ✅ Handle edge cases (very short/long timers)
- ✅ Provide clear voice feedback for all actions
- ✅ Auto-cleanup expired timers via DynamoDB TTL

## Notes for Implementation

- Use `ask_sdk_core.utils.request_util` for timezone extraction
- Reminder API returns reminder IDs - store these for later deletion
- DynamoDB TTL cleanup happens within 48 hours, not immediately
- Test with actual Alexa device for reminder notification UX
- Consider rate limiting (max 1 timer per user to start)
