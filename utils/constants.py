DAYS_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]

DB_FILE = "schedule_db.json"
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "line_token": "",
    "gemini_key": "",
    "remind_1day_hour": 20,
    "remind_hours_before": 2.0,
}

SCHEDULE_KEYS = ("subject", "day", "start_time", "end_time", "room")