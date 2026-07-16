# Ride Ping statuses
PING_STATUS_OPEN = "open"
PING_STATUS_MATCHED = "matched"
PING_STATUS_CANCELLED = "cancelled"
PING_STATUS_EXPIRED = "expired"

# Match Request statuses
REQUEST_STATUS_PENDING = "pending"
REQUEST_STATUS_ACCEPTED = "accepted"
REQUEST_STATUS_DECLINED = "declined"
REQUEST_STATUS_CANCELLED = "cancelled"

# Match statuses
MATCH_STATUS_MATCHED = "matched"
MATCH_STATUS_IN_PROGRESS = "in_progress"
MATCH_STATUS_COMPLETED = "completed"
MATCH_STATUS_CANCELLED = "cancelled"
MATCH_STATUS_DISPUTED = "disputed"

# Fare statuses
FARE_STATUS_PENDING = "pending"
FARE_STATUS_PAID = "paid"
FARE_STATUS_CONFIRMED = "confirmed"
FARE_STATUS_DISPUTED = "disputed"

# Report statuses
REPORT_STATUS_PENDING = "pending"
REPORT_STATUS_REVIEWED = "reviewed"
REPORT_STATUS_RESOLVED = "resolved"
REPORT_STATUS_DISMISSED = "dismissed"

# Report reasons
REPORT_REASON_HARASSMENT = "harassment"
REPORT_REASON_NO_SHOW = "no_show"
REPORT_REASON_PAYMENT_ISSUE = "payment_issue"
REPORT_REASON_FAKE_PROFILE = "fake_profile"
REPORT_REASON_UNSAFE_BEHAVIOR = "unsafe_behavior"
REPORT_REASON_UNSAFE_MEETUP = "unsafe_meetup"

# Gender preferences
GENDER_ANY = "any"
GENDER_MALE = "male"
GENDER_FEMALE = "female"

# Geo constants
DEFAULT_SEARCH_RADIUS_METERS = 200
EXPANDED_SEARCH_RADIUS_METERS = 500
# Find-a-Ride: riders tolerate a longer trip to the pickup point than
# slack on where the ride is actually headed, so the radii differ.
DEFAULT_FIND_PICKUP_RADIUS_METERS = 5000
DEFAULT_FIND_DESTINATION_RADIUS_METERS = 1000

# Timeouts (in minutes)
PING_EXPIRY_MINUTES = 15
DEFAULT_PING_EXPIRY_MINUTES = 30
CHAT_RETENTION_DAYS = 30

# Rating
MIN_RATING = 1
MAX_RATING = 5

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100