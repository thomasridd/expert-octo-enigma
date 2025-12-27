# Alexa Leaving Timer Skill

An Alexa skill that helps families prepare to leave the house on time by creating timers with progressive reminder intervals. Using the Alexa Reminders API, this skill sends native notifications at strategically calculated intervals to help you stay on track.

## Features

- **Progressive Reminders**: Automatic reminders at hourly boundaries (for long timers) plus standard intervals (45, 30, 15, 10, 5, 3, 2, 1 minute, and 30 seconds)
- **Timezone-Aware**: Reminders are scheduled according to your device's timezone
- **Persistent Storage**: Timer state is maintained across skill sessions using DynamoDB
- **Smart Cleanup**: Expired timers are automatically cleaned up using DynamoDB TTL
- **Natural Language**: Supports multiple natural utterances for each command
- **Permission Handling**: Gracefully requests reminder permissions when needed

## Example Usage

```
User: "Alexa, ask Leaving Timer Helper to set a timer for 30 minutes"
Alexa: "Timer set for 30 minutes. I'll remind you at 7 intervals, starting at 30 minutes."

User: "Alexa, ask Leaving Timer Helper how much time do we have"
Alexa: "You have 22 minutes and 15 seconds until you need to leave."

User: "Alexa, ask Leaving Timer Helper to cancel my timer"
Alexa: "I've cancelled your leaving timer and all reminders."
```

## Project Structure

```
leaving-timer-skill/
├── lambda/                         # Lambda function code
│   ├── lambda_function.py          # Main handler with intent handlers
│   ├── reminder_calculator.py      # Interval calculation logic
│   ├── timer_storage.py            # DynamoDB operations
│   ├── requirements.txt            # Python dependencies
│   └── tests/                      # Unit tests
│       ├── test_reminder_calculator.py
│       └── test_timer_storage.py
├── skill-package/                  # Alexa skill configuration
│   ├── skill.json                  # Skill manifest
│   └── interactionModels/
│       └── custom/
│           └── en-GB.json          # UK English interaction model
├── infrastructure/                 # AWS infrastructure
│   └── template.yaml               # AWS SAM template
└── prompt.md                       # Original specification
```

## Prerequisites

- AWS Account
- Python 3.11 or higher
- AWS SAM CLI (for deployment)
- Alexa Developer Account
- ASK CLI (optional, for skill deployment)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd expert-octo-enigma
```

### 2. Install Dependencies Locally (for testing)

```bash
cd lambda
pip install -r requirements.txt
```

### 3. Run Unit Tests

```bash
cd lambda
python -m pytest tests/
```

## Deployment

### Deploy AWS Infrastructure

1. **Configure AWS Credentials**

```bash
aws configure
```

2. **Deploy using AWS SAM**

```bash
cd infrastructure
sam build
sam deploy --guided
```

During the guided deployment:
- Stack Name: `leaving-timer-skill`
- AWS Region: `eu-west-2` (or your preferred region)
- Parameter SkillId: Leave empty initially (update after skill creation)
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Save arguments to configuration file: `Y`

3. **Note the Lambda ARN** from the outputs - you'll need this for the Alexa skill configuration.

### Deploy Alexa Skill

#### Option 1: Using Alexa Developer Console

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click "Create Skill"
3. Skill name: "Leaving Timer Helper"
4. Primary locale: English (GB)
5. Choose "Custom" model and "Provision your own" backend
6. Create the skill

**Configure the Interaction Model:**
1. Go to "Build" tab → "JSON Editor"
2. Copy contents from `skill-package/interactionModels/custom/en-GB.json`
3. Paste and Save Model
4. Click "Build Model"

**Configure the Endpoint:**
1. Go to "Build" tab → "Endpoint"
2. Select "AWS Lambda ARN"
3. Paste your Lambda function ARN
4. Click "Save Endpoints"

**Configure Permissions:**
1. Go to "Build" tab → "Permissions"
2. Enable "Reminders" (alexa::alerts:reminders:skill:readwrite)

#### Option 2: Using ASK CLI

```bash
cd skill-package
ask deploy
```

### Update Lambda with Skill ID

After creating the skill, update your SAM deployment with the skill ID:

```bash
cd infrastructure
sam deploy --parameter-overrides SkillId=amzn1.ask.skill.YOUR-SKILL-ID
```

## Configuration

### Environment Variables

The Lambda function uses these environment variables (automatically set by SAM template):

- `DYNAMODB_TABLE_NAME`: Name of the DynamoDB table (default: `LeavingTimerData`)
- `LOG_LEVEL`: Logging level (default: `INFO`, use `DEBUG` for troubleshooting)

### DynamoDB Table

The skill uses a DynamoDB table with:
- **Partition Key**: `userId` (String)
- **TTL Attribute**: `expiresAt` (Number) - automatically deletes expired timers
- **Billing Mode**: Pay-per-request (scales automatically)

## How It Works

### Reminder Interval Calculation

The skill calculates reminder intervals based on the total duration:

- **For timers ≥ 60 minutes**: Adds reminders at each hour boundary and 30-minute mark
- **Always includes** (if within duration): 45, 30, 15, 10, 5, 3, 2, 1 minute, and 30 seconds
- **Examples**:
  - 20 min timer → 7 reminders at: 15, 10, 5, 3, 2, 1 min, 30 sec
  - 90 min timer → 11 reminders at: 90, 60, 45, 30, 15, 10, 5, 3, 2, 1 min, 30 sec
  - 150 min timer → 13 reminders at: 150, 120, 90, 60, 45, 30, 15, 10, 5, 3, 2, 1 min, 30 sec

### Timer Lifecycle

1. **Create**: User sets a timer with a duration
   - Calculate reminder intervals
   - Create Alexa reminders for each interval
   - Store timer data in DynamoDB with TTL

2. **Check**: User asks for remaining time
   - Retrieve timer from DynamoDB
   - Calculate time remaining
   - Return formatted response

3. **Cancel**: User cancels the timer
   - Retrieve timer from DynamoDB
   - Delete all Alexa reminders
   - Remove timer from DynamoDB

4. **Expire**: Timer completes
   - DynamoDB TTL automatically removes record (within 48 hours)
   - Reminders fire at scheduled times

## Testing

### Unit Tests

Run the test suite:

```bash
cd lambda
python -m pytest tests/ -v
```

Test coverage includes:
- Interval calculation for various durations
- Duration parsing (ISO 8601 format)
- Duration formatting for speech
- Reminder text generation
- DynamoDB operations (with mocks)

### Manual Testing Checklist

- [ ] Set 30-minute timer, verify reminders created
- [ ] Set 2-hour timer, verify hourly + standard reminders
- [ ] Check timer status mid-duration
- [ ] Cancel timer, verify reminders deleted
- [ ] Try setting timer without permission
- [ ] Set timer, then try to set another (replacement flow)
- [ ] Wait for timer to expire naturally

### Testing with Alexa

1. **Enable Testing** in Alexa Developer Console (Test tab)
2. Use the Alexa Simulator or say commands to your device
3. Check CloudWatch Logs for debugging: `/aws/lambda/leaving-timer-skill-LeavingTimerFunction-XXX`

## Troubleshooting

### Permission Errors

If users can't set reminders:
- Ensure the skill manifest includes reminder permissions
- Check that permission card is sent to Alexa app
- User must grant permission in the Alexa app

### Reminders Not Creating

- Check CloudWatch logs for errors
- Verify Lambda has correct permissions
- Ensure timezone is being retrieved correctly
- Check for 100 reminder limit (Alexa platform limit)

### DynamoDB Errors

- Verify Lambda execution role has DynamoDB permissions
- Check table exists and is in same region
- Review CloudWatch logs for specific error messages

### Timer Not Found

- Check if timer expired (verify DynamoDB entry)
- Ensure user ID is consistent across invocations
- Check for DynamoDB connectivity issues

## Cost Estimation

This skill uses serverless AWS services with pay-per-use pricing:

- **Lambda**: Free tier includes 1M requests/month
- **DynamoDB**: Free tier includes 25GB storage + 25 RCU/WCU
- **CloudWatch Logs**: First 5GB per month free

For typical family use (a few timers per day), costs should remain in AWS free tier.

## Limitations

- One active timer per user
- Maximum timer duration: 24 hours
- Subject to Alexa's 100 reminder limit per user
- DynamoDB TTL cleanup happens within 48 hours (not immediate)
- UK English only (can be extended to other locales)

## Future Enhancements

Potential improvements:
- [ ] Multiple simultaneous timers per user
- [ ] Named timers ("morning timer", "school timer")
- [ ] Custom interval configurations
- [ ] Additional locales (en-US, en-CA, etc.)
- [ ] Recurring/scheduled timers
- [ ] Integration with calendar events
- [ ] Voice customization for reminder messages

## Contributing

Contributions are welcome! Please ensure:
- Unit tests pass
- New features include tests
- Code follows existing style
- Update documentation

## License

This project is provided as-is for educational and personal use.

## Support

For issues or questions:
- Check CloudWatch Logs for errors
- Review the [Alexa Skills Kit Documentation](https://developer.amazon.com/docs/ask-overviews/build-skills-with-the-alexa-skills-kit.html)
- See `prompt.md` for detailed implementation specification

## Acknowledgments

Built with:
- [Alexa Skills Kit SDK for Python](https://github.com/alexa/alexa-skills-kit-sdk-for-python)
- [AWS SAM](https://aws.amazon.com/serverless/sam/)
- [Alexa Reminders API](https://developer.amazon.com/docs/smapi/alexa-reminders-api-reference.html)
