from datetime import datetime, timedelta, timezone
from utils.constants import DAYS_TH


def get_bangkok_time() -> datetime:
    tz_bangkok = timezone(timedelta(hours=7))
    return datetime.now(tz_bangkok).replace(tzinfo=None)


def today_name() -> str:
    return DAYS_TH[get_bangkok_time().weekday()]


def parse_time_to_minutes(time_str: str) -> int:
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def minutes_to_str(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def get_classes_for_day(schedule: list, day: str) -> list:
    classes = [c for c in schedule if c["day"] == day]
    return sorted(classes, key=lambda x: x["start_time"])


def get_class_status(classes: list, now: datetime | None = None):
    now = now or get_bangkok_time()
    now_min = now.hour * 60 + now.minute

    current = None
    next_class = None

    for c in classes:
        start = parse_time_to_minutes(c["start_time"])
        end = parse_time_to_minutes(c["end_time"])

        if start <= now_min <= end:
            current = c
        elif start > now_min and next_class is None:
            next_class = c

    return current, next_class


def format_countdown(target_time: str, now: datetime | None = None) -> str:
    now = now or get_bangkok_time()
    target = datetime.strptime(
        f"{now.strftime('%Y-%m-%d')} {target_time}", "%Y-%m-%d %H:%M"
    )
    diff = target - now
    if diff.total_seconds() <= 0:
        return "ถึงเวลาแล้ว"

    hours, rem = divmod(int(diff.total_seconds()), 3600)
    mins = rem // 60
    if hours > 0:
        return f"อีก {hours} ชม. {mins} น."
    return f"อีก {mins} น."


def class_duration_hours(start: str, end: str) -> float:
    s = parse_time_to_minutes(start)
    e = parse_time_to_minutes(end)
    return max(0, (e - s) / 60)


def total_hours_today(classes: list) -> float:
    return sum(class_duration_hours(c["start_time"], c["end_time"]) for c in classes)


def get_class_state(c: dict, now: datetime | None = None) -> str:
    now = now or get_bangkok_time()
    now_min = now.hour * 60 + now.minute
    start = parse_time_to_minutes(c["start_time"])
    end = parse_time_to_minutes(c["end_time"])

    if start <= now_min <= end:
        return "live"
    if now_min < start:
        return "upcoming"
    return "done"


def is_duplicate(schedule: list, entry: dict, exclude_index: int | None = None) -> bool:
    for i, c in enumerate(schedule):
        if exclude_index is not None and i == exclude_index:
            continue
        if (
            c["subject"] == entry["subject"]
            and c["day"] == entry["day"]
            and c["start_time"] == entry["start_time"]
        ):
            return True
    return False


def check_overlaps(schedule: list, entry: dict, exclude_index: int | None = None) -> list:
    overlaps = []
    e_start = parse_time_to_minutes(entry["start_time"])
    e_end = parse_time_to_minutes(entry["end_time"])
    
    for i, c in enumerate(schedule):
        if exclude_index is not None and i == exclude_index:
            continue
        if c["day"] != entry["day"]:
            continue
        c_start = parse_time_to_minutes(c["start_time"])
        c_end = parse_time_to_minutes(c["end_time"])
        
        # Overlap condition: class start < entry end AND entry start < class end
        if c_start < e_end and e_start < c_end:
            overlaps.append(c)
    return overlaps



def build_timeline_html(classes: list, now: datetime | None = None) -> str:
    if not classes:
        return "<p style='color:#94A3B8;text-align:center;padding:10px;'>ไม่มีตารางเรียนวันนี้</p>"

    now = now or get_bangkok_time()
    
    # Dynamically find the range of hours
    min_hour = 8
    max_hour = 18
    for c in classes:
        sh, _ = map(int, c["start_time"].split(":"))
        eh, _ = map(int, c["end_time"].split(":"))
        if sh < min_hour:
            min_hour = sh
        if eh >= max_hour:
            max_hour = eh + 1
            
    day_start = min_hour * 60
    day_end = max_hour * 60
    total = day_end - day_start
    now_min = now.hour * 60 + now.minute
    
    # Current time vertical indicator
    show_now_line = day_start <= now_min <= day_end
    now_pct = max(0, min(100, ((now_min - day_start) / total) * 100))

    blocks = ""
    for c in classes:
        s = parse_time_to_minutes(c["start_time"])
        e = parse_time_to_minutes(c["end_time"])
        left = max(0, min(100, ((s - day_start) / total) * 100))
        width = max(2, min(100 - left, ((e - s) / total) * 100))
        state = get_class_state(c, now)
        color = {"live": "#EF4444", "upcoming": "#6366F1", "done": "#334155"}[state]
        blocks += f"""
        <div title="{c['subject']} ({c['start_time']}-{c['end_time']})"
             style="position:absolute;left:{left}%;width:{width}%;height:100%;
                    background:{color};border-radius:6px;opacity:0.9;
                    box-shadow:inset 0 0 8px rgba(0,0,0,0.2);
                    display:flex;align-items:center;justify-content:center;
                    font-size:10px;color:white;overflow:hidden;text-overflow:ellipsis;
                    white-space:nowrap;padding:0 4px;font-family:'Kanit', sans-serif;">
            {c['subject']}
        </div>
        """

    now_line_html = f"""
    <div style="position:absolute;left:{now_pct}%;top:0;width:3px;height:100%;
                background:#EF4444;z-index:2;box-shadow:0 0 8px #EF4444;"></div>
    """ if show_now_line else ""

    # Generate labels dynamically
    labels = ""
    step = 2 if (max_hour - min_hour) > 8 else 1
    for h in range(min_hour, max_hour + 1, step):
        pct = ((h * 60 - day_start) / total) * 100
        labels += f'<span style="position:absolute;left:{pct}%;transform:translateX(-50%);">{h:02d}:00</span>'

    html_out = f"""
    <div style="position:relative;height:38px;background:#0F172A;border-radius:10px;
                margin:12px 0 8px;overflow:hidden;border:1px solid rgba(255,255,255,0.06);
                box-shadow:inset 0 2px 4px rgba(0,0,0,0.5);">
        {blocks}
        {now_line_html}
    </div>
    <div style="position:relative;height:20px;color:#64748B;font-size:11px;margin-bottom:15px;font-family:'Kanit', sans-serif;">
        {labels}
    </div>
    """
    return "".join(line.strip() for line in html_out.split("\n"))


def build_weekly_grid_html(schedule: list) -> str:
    if not schedule:
        return "<p style='color:#94A3B8;text-align:center;padding:20px;'>ยังไม่มีวิชาเรียนในระบบ</p>"

    # Find global start and end hours
    min_hour = 8
    max_hour = 18
    for c in schedule:
        sh, _ = map(int, c["start_time"].split(":"))
        eh, _ = map(int, c["end_time"].split(":"))
        if sh < min_hour:
            min_hour = sh
        if eh >= max_hour:
            max_hour = eh + 1

    day_start = min_hour * 60
    day_end = max_hour * 60
    total = day_end - day_start

    # Thai day colors (Hex codes for labels and bars)
    day_colors = {
        "จันทร์": {"bg": "rgba(251, 191, 36, 0.12)", "border": "#FBBF24", "text": "#F59E0B"},
        "อังคาร": {"bg": "rgba(244, 114, 182, 0.12)", "border": "#F472B6", "text": "#EC4899"},
        "พุธ": {"bg": "rgba(52, 211, 153, 0.12)", "border": "#34D399", "text": "#10B981"},
        "พฤหัสบดี": {"bg": "rgba(251, 146, 60, 0.12)", "border": "#FB923C", "text": "#F97316"},
        "ศุกร์": {"bg": "rgba(96, 165, 250, 0.12)", "border": "#60A5FA", "text": "#3B82F6"},
        "เสาร์": {"bg": "rgba(192, 132, 252, 0.12)", "border": "#C084FC", "text": "#8B5CF6"},
        "อาทิตย์": {"bg": "rgba(248, 113, 113, 0.12)", "border": "#F87171", "text": "#EF4444"}
    }

    html = '<div style="display:flex; flex-direction:column; gap:12px; font-family:\'Kanit\', sans-serif;">'
    
    # Header row showing time markers
    header_markers = ""
    step = 2 if (max_hour - min_hour) > 8 else 1
    for h in range(min_hour, max_hour + 1, step):
        pct = ((h * 60 - day_start) / total) * 100
        header_markers += f'<span style="position:absolute;left:{pct}%;transform:translateX(-50%);">{h:02d}:00</span>'
        
    html += f"""
    <div style="display:flex; align-items:center; height:20px; color:#64748B; font-size:11px; margin-bottom:4px; padding-left:100px; position:relative; width:100%;">
        {header_markers}
    </div>
    """

    for day in DAYS_TH:
        day_classes = [c for c in schedule if c["day"] == day]
        colors = day_colors.get(day, {"bg": "rgba(255,255,255,0.05)", "border": "#94A3B8", "text": "#F8FAFC"})
        
        blocks = ""
        for c in day_classes:
            s = parse_time_to_minutes(c["start_time"])
            e = parse_time_to_minutes(c["end_time"])
            left = max(0, min(100, ((s - day_start) / total) * 100))
            width = max(2, min(100 - left, ((e - s) / total) * 100))
            
            blocks += f"""
            <div title="{c['subject']} ({c['start_time']}-{c['end_time']}) @ ห้อง {c.get('room','—')}"
                 style="position:absolute;left:{left}%;width:{width}%;height:100%;
                        background:{colors['bg']}; border: 1px solid {colors['border']};
                        border-radius:6px; display:flex; flex-direction:column; align-items:center;
                        justify-content:center; font-size:10px; color:white; overflow:hidden;
                        text-overflow:ellipsis; white-space:nowrap; padding:0 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                <div style="font-weight:600; color:{colors['text']}; overflow:hidden; text-overflow:ellipsis; width:100%; text-align:center;">{c['subject']}</div>
                <div style="font-size:8px; opacity:0.8; color:#CBD5E1;">{c['start_time']}-{c['end_time']}</div>
            </div>
            """

        html += f"""
        <div style="display:flex; align-items:center; gap:10px; background:#1E293B; padding:8px; border-radius:10px; border:1px solid rgba(255,255,255,0.03);">
            <div style="width:80px; font-weight:600; color:{colors['text']}; border-left:3px solid {colors['border']}; padding-left:8px; font-size:14px;">
                {day}
            </div>
            <div style="flex-grow:1; position:relative; height:34px; background:#0F172A; border-radius:8px; overflow:hidden; border:1px solid rgba(255,255,255,0.05);">
                {blocks if day_classes else '<div style="display:flex; align-items:center; justify-content:center; height:100%; color:#475569; font-size:11px; font-style:italic;">ไม่มีเรียน</div>'}
            </div>
        </div>
        """

    html += '</div>'
    return "".join(line.strip() for line in html.split("\n"))