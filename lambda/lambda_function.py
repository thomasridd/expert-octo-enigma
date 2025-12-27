"""
Main Lambda handler for Alexa Leaving Timer Skill
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_model import Response
from ask_sdk_model.services import ServiceException
from ask_sdk_model.services.reminder_management import (
    ReminderRequest,
    Trigger,
    TriggerType,
    AlertInfo,
    SpokenInfo,
    SpokenText,
    PushNotification,
    PushNotificationStatus
)
from ask_sdk_model.ui import AskForPermissionsConsentCard

import reminder_calculator
import timer_storage

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Permission required for reminders
REMINDER_PERMISSION = 'alexa::alerts:reminders:skill:readwrite'


def get_user_timezone(handler_input: HandlerInput) -> str:
    """
    Fetch timezone from device settings API.

    Args:
        handler_input: Alexa handler input

    Returns:
        Timezone string (e.g., 'Europe/London')
    """
    try:
        service_client_factory = handler_input.service_client_factory
        ups_service = service_client_factory.get_ups_service()
        device_id = handler_input.request_envelope.context.system.device.device_id
        timezone = ups_service.get_system_time_zone(device_id)
        return timezone
    except Exception as e:
        logger.error(f"Error getting timezone: {e}")
        return 'Europe/London'  # Default to UK timezone


def check_reminder_permission(handler_input: HandlerInput) -> bool:
    """
    Check if user has granted reminder permissions.

    Args:
        handler_input: Alexa handler input

    Returns:
        True if permission granted, False otherwise
    """
    permissions = handler_input.request_envelope.context.system.user.permissions
    if not permissions or not permissions.consent_token:
        return False
    return True


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch"""

    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        speak_output = (
            "Welcome to Leaving Timer Helper. "
            "You can set a leaving timer, check your timer, or cancel it. "
            "What would you like to do?"
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class SetLeavingTimerIntentHandler(AbstractRequestHandler):
    """Handler for SetLeavingTimerIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("SetLeavingTimerIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("SetLeavingTimerIntent triggered")

        # Check for reminder permission
        if not check_reminder_permission(handler_input):
            speak_output = (
                "I need permission to set reminders. "
                "I've sent a card to your Alexa app. "
                "Please enable reminders and try again."
            )
            return (
                handler_input.response_builder
                .speak(speak_output)
                .set_card(AskForPermissionsConsentCard(permissions=[REMINDER_PERMISSION]))
                .response
            )

        # Get duration from slot
        slots = handler_input.request_envelope.request.intent.slots
        duration_slot = slots.get('duration')

        if not duration_slot or not duration_slot.value:
            speak_output = "Please specify how long until you need to leave."
            return (
                handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
            )

        try:
            # Parse duration
            duration_str = duration_slot.value
            duration_minutes = reminder_calculator.parse_duration_to_minutes(duration_str)

            # Validate duration
            if duration_minutes <= 0 or duration_minutes > 1440:  # 24 hours max
                speak_output = "Please specify a duration between 1 minute and 24 hours."
                return (
                    handler_input.response_builder
                    .speak(speak_output)
                    .ask(speak_output)
                    .response
                )

            # Check for existing timer
            user_id = handler_input.request_envelope.context.system.user.user_id
            existing_timer = timer_storage.get_active_timer(user_id)

            if existing_timer:
                # Timer exists - in production, would use dialog elicitation
                # For now, we'll replace it
                logger.info(f"Replacing existing timer for user {user_id}")
                # Delete old reminders
                self._delete_reminders(handler_input, existing_timer.reminder_ids)
                timer_storage.delete_timer(user_id)

            # Calculate reminder intervals
            intervals = reminder_calculator.calculate_reminder_intervals(duration_minutes)
            logger.info(f"Calculated {len(intervals)} reminder intervals")

            # Create reminders
            reminder_ids = self._create_reminders(
                handler_input,
                intervals,
                duration_minutes
            )

            if not reminder_ids:
                speak_output = (
                    "Sorry, I couldn't create the reminders. "
                    "Please try again later."
                )
                return (
                    handler_input.response_builder
                    .speak(speak_output)
                    .response
                )

            # Store timer in DynamoDB
            timer_storage.create_timer(user_id, duration_minutes, reminder_ids)

            # Build response
            duration_friendly = reminder_calculator.format_duration_friendly(duration_minutes)
            first_interval = reminder_calculator.format_duration_friendly(int(intervals[0]))

            speak_output = (
                f"Timer set for {duration_friendly}. "
                f"I'll remind you at {len(intervals)} intervals, "
                f"starting at {first_interval}."
            )

            return (
                handler_input.response_builder
                .speak(speak_output)
                .response
            )

        except ValueError as e:
            logger.error(f"Error parsing duration: {e}")
            speak_output = "Sorry, I didn't understand that duration. Please try again."
            return (
                handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
            )
        except Exception as e:
            logger.error(f"Error setting timer: {e}")
            speak_output = "Sorry, I'm having trouble setting your timer right now."
            return (
                handler_input.response_builder
                .speak(speak_output)
                .response
            )

    def _create_reminders(
        self,
        handler_input: HandlerInput,
        intervals: List[float],
        total_duration: int
    ) -> List[str]:
        """Create Alexa reminders for each interval"""
        reminder_ids = []

        try:
            reminder_service = handler_input.service_client_factory.get_reminder_management_service()
            timezone = get_user_timezone(handler_input)
            now = datetime.utcnow()

            for interval in intervals:
                # Calculate trigger time
                trigger_time = now + timedelta(minutes=(total_duration - interval))

                # Generate reminder text
                reminder_text = reminder_calculator.generate_reminder_text(interval)

                # Create reminder request
                reminder_request = ReminderRequest(
                    trigger=Trigger(
                        trigger_type=TriggerType.SCHEDULED_ABSOLUTE,
                        scheduled_time=trigger_time.isoformat() + 'Z',
                        time_zone_id=timezone
                    ),
                    alert_info=AlertInfo(
                        spoken_info=SpokenInfo(
                            content=[SpokenText(text=reminder_text)]
                        )
                    ),
                    push_notification=PushNotification(
                        status=PushNotificationStatus.ENABLED
                    )
                )

                # Create reminder
                reminder_response = reminder_service.create_reminder(reminder_request)
                reminder_ids.append(reminder_response.alert_token)
                logger.info(f"Created reminder: {reminder_response.alert_token}")

            return reminder_ids

        except ServiceException as e:
            logger.error(f"Service exception creating reminders: {e}")
            if e.status_code == 403:
                logger.error("Permission denied for reminders")
            return []
        except Exception as e:
            logger.error(f"Error creating reminders: {e}")
            return []

    def _delete_reminders(self, handler_input: HandlerInput, reminder_ids: List[str]):
        """Delete a list of reminders"""
        try:
            reminder_service = handler_input.service_client_factory.get_reminder_management_service()
            for reminder_id in reminder_ids:
                try:
                    reminder_service.delete_reminder(reminder_id)
                    logger.info(f"Deleted reminder: {reminder_id}")
                except Exception as e:
                    logger.error(f"Error deleting reminder {reminder_id}: {e}")
        except Exception as e:
            logger.error(f"Error accessing reminder service: {e}")


class CheckTimerIntentHandler(AbstractRequestHandler):
    """Handler for CheckTimerIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("CheckTimerIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("CheckTimerIntent triggered")

        try:
            user_id = handler_input.request_envelope.context.system.user.user_id
            timer = timer_storage.get_active_timer(user_id)

            if not timer:
                speak_output = "You don't have an active leaving timer."
                return (
                    handler_input.response_builder
                    .speak(speak_output)
                    .response
                )

            # Calculate remaining time
            end_time = datetime.fromisoformat(timer.end_time.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=end_time.tzinfo)
            remaining = end_time - now

            if remaining.total_seconds() <= 0:
                speak_output = "Your timer has finished."
                timer_storage.delete_timer(user_id)
                return (
                    handler_input.response_builder
                    .speak(speak_output)
                    .response
                )

            # Format remaining time
            total_seconds = int(remaining.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60

            if minutes > 0:
                speak_output = f"You have {minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''} until you need to leave."
            else:
                speak_output = f"You have {seconds} second{'s' if seconds != 1 else ''} until you need to leave."

            return (
                handler_input.response_builder
                .speak(speak_output)
                .response
            )

        except Exception as e:
            logger.error(f"Error checking timer: {e}")
            speak_output = "Sorry, I'm having trouble accessing your timer right now."
            return (
                handler_input.response_builder
                .speak(speak_output)
                .response
            )


class CancelTimerIntentHandler(AbstractRequestHandler):
    """Handler for CancelTimerIntent"""

    def can_handle(self, handler_input):
        return is_intent_name("CancelTimerIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("CancelTimerIntent triggered")

        try:
            user_id = handler_input.request_envelope.context.system.user.user_id
            timer = timer_storage.get_active_timer(user_id)

            if not timer:
                speak_output = "You don't have an active leaving timer to cancel."
                return (
                    handler_input.response_builder
                    .speak(speak_output)
                    .response
                )

            # Delete all reminders
            reminder_service = handler_input.service_client_factory.get_reminder_management_service()
            for reminder_id in timer.reminder_ids:
                try:
                    reminder_service.delete_reminder(reminder_id)
                    logger.info(f"Deleted reminder: {reminder_id}")
                except Exception as e:
                    logger.error(f"Error deleting reminder {reminder_id}: {e}")

            # Delete timer from DynamoDB
            timer_storage.delete_timer(user_id)

            speak_output = "I've cancelled your leaving timer and all reminders."

            return (
                handler_input.response_builder
                .speak(speak_output)
                .response
            )

        except Exception as e:
            logger.error(f"Error canceling timer: {e}")
            speak_output = "Sorry, I'm having trouble canceling your timer right now."
            return (
                handler_input.response_builder
                .speak(speak_output)
                .response
            )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent"""

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = (
            "With Leaving Timer Helper, you can set a timer to help you prepare to leave. "
            "Just say, set a leaving timer for 30 minutes, and I'll remind you at regular intervals. "
            "You can also check your timer or cancel it. "
            "What would you like to do?"
        )

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelAndStopIntentHandler(AbstractRequestHandler):
    """Handler for Cancel and Stop Intents"""

    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input) or
            is_intent_name("AMAZON.StopIntent")(handler_input)
        )

    def handle(self, handler_input):
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End"""

    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # Cleanup logic here if needed
        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """Fallback handler that reflects the intent name"""

    def can_handle(self, handler_input):
        return is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        intent_name = handler_input.request_envelope.request.intent.name
        speak_output = f"You just triggered {intent_name}. I'm not sure how to handle that yet."

        return (
            handler_input.response_builder
            .speak(speak_output)
            .response
        )


class ErrorHandler(AbstractExceptionHandler):
    """Generic error handler"""

    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(f"Error handled: {exception}", exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


# Initialize skill builder
sb = SkillBuilder()

# Register request handlers
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetLeavingTimerIntentHandler())
sb.add_request_handler(CheckTimerIntentHandler())
sb.add_request_handler(CancelTimerIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())

# Register exception handler
sb.add_exception_handler(ErrorHandler())

# Lambda handler
lambda_handler = sb.lambda_handler()
