"""Constants for the Spring Input Booleans integration."""

DOMAIN = "spring_input_booleans"

# Configuration keys for individual devices
CONF_ENTITY_ID = "entity_id"
CONF_DELAY_SECONDS = "delay_seconds"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_PHONE_ENTITY_IDS = "phone_entity_ids"

# Default values
DEFAULT_DELAY_SECONDS = 2
DEFAULT_ENABLE_NOTIFICATIONS = False
DEFAULT_NOTIFICATION_SERVICE = "notify"

# Notification service options
NOTIFICATION_SERVICES = {
    "notify": "All configured notification services",
    "mobile_app": "Mobile app notifications", 
    "telegram": "Telegram",
    "pushbullet": "Pushbullet",
    "email": "Email",
    "custom": "Custom notification service"
}