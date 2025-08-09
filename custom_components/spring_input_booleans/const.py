"""Constants for the Spring Input Booleans integration."""

DOMAIN = "spring_input_booleans"

# Configuration keys
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_PHONE_ENTITY_IDS = "phone_entity_ids"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_MONITORED_ENTITIES = "monitored_entities"
CONF_AUTO_DISCOVER = "auto_discover"

# Default values
DEFAULT_NOTIFICATION_SERVICE = "notify"
DEFAULT_ENABLE_NOTIFICATIONS = True
DEFAULT_AUTO_DISCOVER = True

# Notification service options
NOTIFICATION_SERVICES = {
    "notify": "All configured notification services",
    "mobile_app": "Mobile app notifications",
    "telegram": "Telegram",
    "pushbullet": "Pushbullet", 
    "email": "Email",
    "custom": "Custom notification service"
}