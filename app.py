import json
import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
from PIL import Image

from utils.constants import DAYS_TH, DEFAULT_CONFIG
from utils.storage import (
    load_schedule_by_user, 
    save_schedule_by_user, 
    load_config_by_user, 
    save_config_by_user,
    authenticate_user,
    register_user,
    get_user_line_id,
    update_user_line_id
)
from utils.schedule import (
    get_bangkok_time,
    today_name,
    get_classes_for_day,
    get_class_status,
    format_countdown,
    total_hours_today,
    get_class_state,
    is_duplicate,
    build_timeline_html,
    check_overlaps,
    build_weekly_grid_html,
)
from utils.styles import (
    inject_global_css,
    render_metric_card,
    render_status_banner,
    render_class_card,
)
from utils.ai_scanner import scan_schedule_image, CENTRAL_GEMINI_API_KEY
from utils.notifications import send_line_notify


def render_live_countdown(next_class: dict) -> str:
    if not next_class:
        return ""
    
    target_time = next_class['start_time'] # "HH:MM"
    subject = next_class['subject']
    room = next_class.get('room') or 'ไม่ระบุห้อง'
    
    html_out = f"""
    <div class="live-countdown-card">
        <div class="live-countdown-title">⏱️ นับถอยหลังเข้าเรียนวิชาถัดไป</div>
        <div class="live-countdown-subject">{subject} · ห้อง {room}</div>
        <div id="live-timer" class="live-timer-value">--:--:--</div>
    </div>
    <script>
    (function() {{
        var targetTimeStr = "{target_time}";
        var parts = targetTimeStr.split(":");
        var targetDate = new Date();
        targetDate.setHours(parseInt(parts[0], 10));
        targetDate.setMinutes(parseInt(parts[1], 10));
        targetDate.setSeconds(0);
        targetDate.setMilliseconds(0);
        
        function updateTimer() {{
            var now = new Date();
            var diff = targetDate - now;
            var timerEl = document.getElementById("live-timer");
            if (!timerEl) return;
            
            if (diff <= 0) {{
                timerEl.innerHTML = "ถึงเวลาเรียนแล้ว!";
                timerEl.style.color = "#34D399";
                return;
            }}
            
            var hours = Math.floor(diff / (1000 * 60 * 60));
            var mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            var secs = Math.floor((diff % (1000 * 60)) / 1000);
            
            var hStr = hours < 10 ? "0" + hours : hours;
            var mStr = mins < 10 ? "0" + mins : mins;
            var sStr = secs < 10 ? "0" + secs : secs;
            
            timerEl.innerHTML = hStr + ":" + mStr + ":" + sStr;
        }}
        
        updateTimer();
        var timerId = setInterval(updateTimer, 1000);
    }})();
    </script>
    """
    return "".join(line.strip() for line in html_out.split("\n"))



# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Class AI | Smart Reminder",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

# ── Session state init ─────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

if "schedule" not in st.session_state:
    st.session_state.schedule = []
if "scan_preview" not in st.session_state:
    st.session_state.scan_preview = None

# ระบบจัดการสเตตนำทาง (Navigation State Sync)
if "current_menu" not in st.session_state:
    st.session_state["current_menu"] = "📋 แดชบอร์ด"

# ตรวจเช็กหากมีการกดปุ่มข้ามหน้ามาจากหน้าอื่น
if "_nav" in st.session_state:
    st.session_state["current_menu"] = st.session_state.pop("_nav")


def persist_schedule():
    if st.session_state.logged_in and st.session_state.user_id is not None:
        save_schedule_by_user(st.session_state.user_id, st.session_state.schedule)


# ══════════════════════════════════════════════════════════════
# AUTHENTICATION SCREEN (ระบบล็อกอิน/สมัครสมาชิก)
# ══════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    col_auth_left, col_auth_mid, col_auth_right = st.columns([1, 2, 1])
    
    with col_auth_mid:
        st.markdown(
            "<div style='text-align: center; margin-bottom: 25px;'>"
            "<h1 style='font-size: 2.8rem; font-weight: 800; color: #4F46E5; margin-bottom: 5px;'>🎓 Class AI</h1>"
            "<p style='color: #6B7280; font-size: 1.1rem;'>Smart Schedule & Notification Portal</p>"
            "</div>", 
            unsafe_allow_html=True
        )
        
        tab_login, tab_register = st.tabs(["🔑 เข้าสู่ระบบ", "📝 สมัครใช้งานใหม่"])
        
        with tab_login:
            with st.form("login_form"):
                st.subheader("Login to your account")
                username_input = st.text_input("ชื่อผู้ใช้งาน (Username)", placeholder="กรอกชื่อผู้ใช้งาน...")
                password_input = st.text_input("รหัสผ่าน (Password)", type="password", placeholder="กรอกรหัสผ่าน...")
                
                login_submitted = st.form_submit_button("⚡ เข้าสู่ระบบ", use_container_width=True, type="primary")
                
                if login_submitted:
                    if not username_input.strip() or not password_input.strip():
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                    else:
                        # เรียกฟังก์ชันตรวจสอบรหัสผ่าน (คืนค่า user_id หรือ None)
                        user_id_result = authenticate_user(username_input.strip(), password_input.strip())
                        if user_id_result:
                            # ดึงค่า id ตัวแรกออกมาจาก tuple (ป้องกันปัญหา sqlite3.ProgrammingError)
                            user_id = user_id_result[0] if isinstance(user_id_result, (tuple, list)) else user_id_result
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_id
                            st.session_state.username = username_input.strip()
                            # โหลดข้อมูลเฉพาะของ User
                            st.session_state.schedule = load_schedule_by_user(user_id)
                            st.toast(f"ยินดีต้อนรับกลับมาคุณ {username_input}! 👋", icon="✅")
                            st.rerun()
                        else:
                            st.error("❌ ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
                            
        with tab_register:
            with st.form("register_form"):
                st.subheader("Create new account")
                reg_username = st.text_input("กำหนดชื่อผู้ใช้งาน (Username) *", placeholder="ภาษาอังกฤษหรือตัวเลข...")
                reg_password = st.text_input("กำหนดรหัสผ่าน (Password) *", type="password", placeholder="อย่างน้อย 4 ตัวอักษร...")
                reg_password_conf = st.text_input("ยืนยันรหัสผ่านอีกครั้ง *", type="password", placeholder="ป้อนรหัสผ่านให้ตรงกัน...")
                
                reg_submitted = st.form_submit_button("✨ สมัครสมาชิก", use_container_width=True)
                
                if reg_submitted:
                    if not reg_username.strip() or not reg_password.strip():
                        st.error("กรุณาระบุข้อมูลในช่องสำคัญ (*) ให้ครบถ้วน")
                    elif reg_password != reg_password_conf:
                        st.error("❌ รหัสผ่านทั้งสองช่องไม่ตรงกัน กรุณาตรวจสอบอีกครั้ง")
                    elif len(reg_password) < 4:
                        st.error("รหัสผ่านควรมีความยาวอย่างน้อย 4 ตัวอักษร")
                    else:
                        # เรียกฟังก์ชันสมัครสมาชิก (คืนค่า True/False)
                        success = register_user(reg_username.strip(), reg_password.strip())
                        if success:
                            st.success("🎉 สมัครสมาชิกสำเร็จ! คุณสามารถใช้ชื่อผู้ใช้นี้ล็อกอินได้ทันที")
                        else:
                            st.error("⚠️ ชื่อผู้ใช้นี้มีผู้อื่นใช้งานแล้ว กรุณาเลือกชื่อใหม่อีกครั้ง")

# ══════════════════════════════════════════════════════════════
# MAIN APPLICATION SCREEN (เมื่อล็อกอินสำเร็จแล้วเท่านั้น)
# ══════════════════════════════════════════════════════════════
else:
    # ดึง config ของผู้ใช้ที่เข้าสู่ระบบ
    config = load_config_by_user(st.session_state.user_id)
    now = get_bangkok_time()
    today = today_name()


    # ── Sidebar ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"## 🧠 Class AI")
        st.markdown(f"สวัสดีคุณ **{st.session_state.username}** 👋")
        st.caption("Smart Class Reminder")
        st.divider()

        menu_options = ["📋 แดชบอร์ด", "📅 ตารางเรียน", "📸 สแกนตาราง", "➕ เพิ่มวิชา", "⚙️ ตั้งค่า", "ℹ️ ข้อมูลระบบ"]
        
        if st.session_state["current_menu"] not in menu_options:
            st.session_state["current_menu"] = "📋 แดชบอร์ด"

        menu = st.radio(
            "เมนูหลัก",
            menu_options,
            index=menu_options.index(st.session_state["current_menu"]),
            label_visibility="collapsed",
            key="main_menu_radio"
        )
        st.session_state["current_menu"] = menu

        st.divider()
        st.metric("📅 วันนี้", f"วัน{today}")
        st.metric("⏰ เวลาปัจจุบัน", now.strftime("%H:%M น."))

        today_classes_sidebar = get_classes_for_day(st.session_state.schedule, today)
        _, next_cls = get_class_status(today_classes_sidebar)
        if next_cls:
            st.info(f"วิชาถัดไป: **{next_cls['subject']}** ({next_cls['start_time']})")
        elif today_classes_sidebar:
            st.success("เรียนครบหมดแล้ววันนี้ 🎉")
        else:
            st.warning("ไม่มีตารางเรียนวันนี้")

        line_user_id = get_user_line_id(st.session_state.user_id)
        line_ok = "✅" if line_user_id else "❌"
        gemini_ok = "✅" if (CENTRAL_GEMINI_API_KEY and CENTRAL_GEMINI_API_KEY != "ใส่_GEMINI_KEY_ส่วนกลางตรงนี้") else "❌"
        st.caption(f"LINE {line_ok} · Gemini {gemini_ok}")
        
        # ปุ่ม Logout ออกจากระบบ
        st.divider()
        if st.sidebar.button("🚪 ออกจากระบบ (Logout)", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.schedule = []
            st.session_state.scan_preview = None
            st.rerun()


    def page_header(title: str, subtitle: str = ""):
        sub_html = f"<div class='hero-sub'>{subtitle}</div>" if subtitle else ""
        st.markdown(
            f"<div class='hero-header'><div><h1 class='hero-title'>{title}</h1>{sub_html}</div></div>",
            unsafe_allow_html=True,
        )


    # ══════════════════════════════════════════════════════════════
    # PAGE 1: Dashboard
    # ══════════════════════════════════════════════════════════════
    if st.session_state["current_menu"] == "📋 แดชบอร์ด":
        page_header("📋 แดชบอร์ด", f"วัน{today} · {now.strftime('%d/%m/%Y')}")

        today_classes = get_classes_for_day(st.session_state.schedule, today)
        current, next_class = get_class_status(today_classes)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            val = current["subject"] if current else ("ไม่มีเรียน" if today_classes else "—")
            render_metric_card("กำลังเรียน", val, "metric-value--live" if current else "")
        with m2:
            if next_class:
                val = f"{next_class['subject']} ({format_countdown(next_class['start_time'])})"
            else:
                val = "ไม่มีเรียน" if today_classes else "—"
            render_metric_card("วิชาถัดไป", val, "metric-value--next" if next_class else "")
        with m3:
            render_metric_card("วิชาวันนี้", str(len(today_classes)))
        with m4:
            hours = total_hours_today(today_classes)
            render_metric_card("ชั่วโมงเรียนรวม", f"{hours:.1f} ชม.")

        st.markdown("---")

        if current:
            render_status_banner(
                "now",
                "กำลังเรียนอยู่ขณะนี้",
                f"{current['subject']} · ห้อง {current.get('room', '—')} · เลิกเรียน {current['end_time']}",
            )
        elif next_class:
            st.markdown(render_live_countdown(next_class), unsafe_allow_html=True)
        elif not today_classes:
            render_status_banner("free", "วันนี้ไม่มีเรียน", "วันพักผ่อนสบายๆ ไม่มีตารางเรียนในระบบ")
        else:
            render_status_banner("free", "เลิกเรียนแล้ว", "เย้! เรียนครบถ้วนทุกวิชาของวันนี้แล้วครับ 🎉")

        st.subheader("ไทม์ไลน์วันนี้")
        st.markdown(build_timeline_html(today_classes), unsafe_allow_html=True)

        st.subheader("รายวิชาวันนี้")
        if today_classes:
            for c in sorted(today_classes, key=lambda x: x["start_time"]):
                render_class_card(c, get_class_state(c))
        else:
            st.markdown('<div class="empty-state"><h3>🎉 ยังไม่มีตารางเรียนวันนี้</h3><p>คุณสามารถสแกนรูปตารางเรียนหรือเพิ่มวิชาด้วยตนเองได้ด่วนที่ปุ่มด้านล่าง</p></div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📸 ไปสแกนตาราง", use_container_width=True):
                    st.session_state["current_menu"] = "📸 สแกนตาราง"
                    st.rerun()
            with c2:
                if st.button("➕ เพิ่มวิชา", use_container_width=True):
                    st.session_state["current_menu"] = "➕ เพิ่มวิชา"
                    st.rerun()

        # กราฟวิเคราะห์ภาระงานเรียนสำหรับส่งอาจารย์
        if st.session_state.schedule:
            st.divider()
            st.subheader("📊 การวิเคราะห์ภาระงานเรียน (Study Load Analytics)")
            
            # Calculate hours per day
            days_order = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
            day_hours = {d: 0.0 for d in days_order}
            subject_hours = {}
            
            for c in st.session_state.schedule:
                try:
                    sh, sm = map(int, c["start_time"].split(":"))
                    eh, em = map(int, c["end_time"].split(":"))
                    hours = (eh * 60 + em - (sh * 60 + sm)) / 60.0
                    if hours < 0: 
                        hours += 24.0
                    
                    day = c["day"]
                    if day in day_hours:
                        day_hours[day] += hours
                        
                    sub = c["subject"]
                    subject_hours[sub] = subject_hours.get(sub, 0.0) + hours
                except Exception:
                    pass
            
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.caption("📈 จำนวนชั่วโมงเรียนรวมรายวัน")
                day_df = pd.DataFrame([
                    {"วัน": d, "ชั่วโมงเรียนรวม (ชม.)": day_hours[d]} 
                    for d in days_order if day_hours[d] > 0
                ])
                if not day_df.empty:
                    st.bar_chart(day_df.set_index("วัน"), use_container_width=True)
                else:
                    st.info("ไม่มีวิชาเรียนที่บันทึกข้อมูลเวลาเรียบร้อย")
                    
            with c_chart2:
                st.caption("📚 ชั่วโมงเรียนสะสมรายวิชา")
                sub_df = pd.DataFrame([
                    {"วิชา": s, "ชั่วโมงเรียน (ชม.)": h} 
                    for s, h in subject_hours.items()
                ]).sort_values(by="ชั่วโมงเรียน (ชม.)", ascending=False)
                if not sub_df.empty:
                    st.bar_chart(sub_df.set_index("วิชา"), use_container_width=True)
                else:
                    st.info("ไม่มีข้อมูลวิชาเรียน")


    # ══════════════════════════════════════════════════════════════
    # PAGE 2: Full schedule
    # ══════════════════════════════════════════════════════════════
    elif st.session_state["current_menu"] == "📅 ตารางเรียน":
        page_header("📅 ตารางเรียนทั้งหมด", "ตรวจสอบรายการวิชาเรียนสะสมในระบบ")

        search_query = st.text_input("🔍 ค้นหาวิชาเรียน", placeholder="พิมพ์เพื่อค้นหาตามชื่อวิชาเรียน...")

        tab_week, tab_grid, tab_all = st.tabs([
            "📆 มุมมองภาพรวมรายสัปดาห์ (รายวัน)",
            "📊 ตารางเรียนรายสัปดาห์ (Grid)",
            "📋 แก้ไข/ลบรายรายการ"
        ])

        with tab_week:
            cols = st.columns(7)
            for i, day_item in enumerate(DAYS_TH):
                with cols[i]:
                    st.markdown(f"### {day_item}")
                    day_classes = [c for c in st.session_state.schedule if c["day"] == day_item]
                    if search_query:
                        day_classes = [c for c in day_classes if search_query.lower() in c["subject"].lower()]
                    
                    if day_classes:
                        for c in sorted(day_classes, key=lambda x: x["start_time"]):
                            st.info(f"📖 **{c['subject']}**\n\n⏱️ {c['start_time']} - {c['end_time']}\n\n🚪 ห้อง: {c.get('room','—')}")
                    else:
                        st.caption("ไม่มีวิชาเรียน")

        with tab_grid:
            grid_schedule = st.session_state.schedule
            if search_query:
                grid_schedule = [c for c in grid_schedule if search_query.lower() in c["subject"].lower()]
            
            st.markdown(build_weekly_grid_html(grid_schedule), unsafe_allow_html=True)

        with tab_all:
            if not st.session_state.schedule:
                st.info("ยังไม่มีข้อมูลตารางเรียนในระบบฐานข้อมูล")
            else:
                visible_count = 0
                for idx, c in enumerate(st.session_state.schedule):
                    if search_query and search_query.lower() not in c["subject"].lower():
                        continue
                    visible_count += 1
                    with st.expander(f"📍 [{c['day']}] {c['start_time']} - {c['end_time']}  👉  {c['subject']}", expanded=False):
                        with st.form(f"edit_{idx}"):
                            sub = st.text_input("ชื่อวิชาเรียน", value=c["subject"])
                            day = st.selectbox("วันเรียน", DAYS_TH, index=DAYS_TH.index(c["day"]))
                            t1, t2 = st.columns(2)
                            with t1:
                                sh, sm = map(int, c["start_time"].split(":"))
                                start = st.time_input("เวลาเริ่ม", value=time(sh, sm), key=f"s_{idx}")
                            with t2:
                                eh, em = map(int, c["end_time"].split(":"))
                                end = st.time_input("เวลาเลิก", value=time(eh, em), key=f"e_{idx}")
                            room = st.text_input("ห้องเรียน", value=c.get("room", ""))

                            c1, c2 = st.columns(2)
                            with c1:
                                save_btn = st.form_submit_button("💾 บันทึกการแก้ไข", use_container_width=True)
                            with c2:
                                del_btn = st.form_submit_button("🗑️ ลบวิชานี้", use_container_width=True)

                            if save_btn:
                                updated = {
                                    "subject": sub.strip(),
                                    "day": day,
                                    "start_time": start.strftime("%H:%M"),
                                    "end_time": end.strftime("%H:%M"),
                                    "room": room.strip(),
                                }
                                
                                # Check overlaps
                                overlaps = check_overlaps(st.session_state.schedule, updated, exclude_index=idx)
                                
                                if is_duplicate(st.session_state.schedule, updated, exclude_index=idx):
                                    st.error("ไม่สามารถบันทึกได้เนื่องจากวันและเวลาซ้ำกับวิชาอื่นตรงกันทุกประการ")
                                else:
                                    if overlaps:
                                        st.warning("⚠️ เวลาเรียนคาบนี้ซ้อนทับกับวิชาอื่นในระบบ:")
                                        for o in overlaps:
                                            st.write(f"- {o['subject']} ({o['start_time']} - {o['end_time']})")
                                    st.session_state.schedule[idx] = updated
                                    persist_schedule()
                                    st.toast("อัปเดตวิชาเรียบร้อย")
                                    st.rerun()

                            if del_btn:
                                st.session_state.schedule.pop(idx)
                                persist_schedule()
                                st.toast("ลบข้อมูลวิชาออกแล้ว")
                                st.rerun()
                if visible_count == 0:
                    st.info("ไม่พบวิชาเรียนที่ตรงกับคำค้นหา")


    # ══════════════════════════════════════════════════════════════
    # PAGE 3: AI Scanner
    # ══════════════════════════════════════════════════════════════
    elif st.session_state["current_menu"] == "📸 สแกนตาราง":
        page_header("📸 AI Schedule Scanner", "แปลงรูปถ่ายตารางเรียนให้เป็นดิจิทัลด้วย Gemini API")

        if not config.get("gemini_key"):
            st.warning("⚠️ กรุณาตั้งค่าคอนฟิกตัวแปร Gemini API Key ที่หน้าเมนู ⚙️ ตั้งค่า ก่อนเริ่มใช้งานสแกนภาพ")
        else:
            uploaded = st.file_uploader("อัปโหลดไฟล์ภาพตารางเรียนของคุณ", type=["jpg", "jpeg", "png", "webp"])

            if uploaded:
                col_img, col_info = st.columns([1, 1])
                with col_img:
                    st.image(uploaded, caption="ภาพตารางเรียนต้นฉบับ", use_container_width=True)
                with col_info:
                    st.markdown("### 🤖 ขั้นตอนการทำงานของระบบ AI")
                    st.write("1. ตรวจสอบความชัดเจนของรูปภาพ\n2. กดปุ่มวิเคราะห์เพื่อส่งข้อมูลหาโมเดล AI\n3. ระบบจะแปลงผลลัพธ์ลงตารางดิจิทัลให้อัตโนมัติ")

                    if st.button("🧠 สั่ง AI เริ่มแกะข้อมูลตารางเรียน", type="primary", use_container_width=True):
                        with st.spinner("AI กำลังวิเคราะห์และแยกวิชาเรียนให้โปรดรอสักครู่..."):
                            try:
                                img = Image.open(uploaded)
                                st.session_state.scan_preview = scan_schedule_image(img)
                                st.success(f"🎉 ตรวจสอบข้อมูลเสร็จสิ้น! พบรายวิชาทั้งหมด {len(st.session_state.scan_preview)} รายการ")
                            except Exception as e:
                                st.error(f"การวิเคราะห์รูปภาพล้มเหลวเนื่องจาก: {e}")
                                st.session_state.scan_preview = None

            if st.session_state.scan_preview:
                st.subheader("👀 ตรวจสอบความถูกต้องของข้อมูลจาก AI")
                df = pd.DataFrame(st.session_state.scan_preview)
                st.dataframe(df, use_container_width=True, hide_index=True)

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("✅ ยืนยันเพิ่มเข้าตารางหลัก", type="primary", use_container_width=True):
                        st.session_state.schedule.extend(st.session_state.scan_preview)
                        persist_schedule()
                        st.session_state.scan_preview = None
                        st.toast("เพิ่มวิชาทั้งหมดลงระบบแล้ว!")
                        st.rerun()
                with c2:
                    if st.button("🔄 ล้างและบันทึกแทนที่ตารางเก่า", use_container_width=True):
                        st.session_state.schedule = list(st.session_state.scan_preview)
                        persist_schedule()
                        st.session_state.scan_preview = None
                        st.toast("เขียนทับตารางเรียนเดิมเรียบร้อย!")
                        st.rerun()
                with c3:
                    if st.button("❌ ยกเลิกและล้างสเตต", use_container_width=True):
                        st.session_state.scan_preview = None
                        st.rerun()


    # ══════════════════════════════════════════════════════════════
    # PAGE 4: Manual add
    # ══════════════════════════════════════════════════════════════
    elif st.session_state["current_menu"] == "➕ เพิ่มวิชา":
        page_header("➕ เพิ่มวิชาเรียน", "เพิ่มตารางเรียนแมนนวลด้วยตัวคุณเอง")

        with st.form("add_class", clear_on_submit=True):
            sub = st.text_input("ชื่อวิชาเรียน *", placeholder="เช่น Advance Computer Programming")
            day = st.selectbox("วันเรียน *", DAYS_TH, index=DAYS_TH.index(today))
            c1, c2 = st.columns(2)
            with c1:
                start = st.time_input("เวลาเริ่มเรียน *", value=time(9, 0))
            with c2:
                end = st.time_input("เวลาเลิกเรียน *", value=time(10, 30))
            room = st.text_input("ห้องเรียน / สถานที่เรียน", placeholder="เช่น ห้องบรรยาย 402 หรือ เรียนออนไลน์ WebEx")

            submitted = st.form_submit_button("💾 ยืนยันบันทึกวิชาเรียน", type="primary", use_container_width=True)

            if submitted:
                if not sub.strip():
                    st.error("กรุณาระบุชื่อวิชาเรียนด้วยครับ")
                elif start >= end:
                    st.error("เวลาเลิกเรียนต้องอยู่หลังเวลาเริ่มเรียนเสมอ")
                else:
                    entry = {
                        "subject": sub.strip(),
                        "day": day,
                        "start_time": start.strftime("%H:%M"),
                        "end_time": end.strftime("%H:%M"),
                        "room": room.strip() if room.strip() else "ไม่ระบุห้องเรียน",
                    }
                    
                    # Check duplication and overlap
                    overlaps = check_overlaps(st.session_state.schedule, entry)
                    
                    if is_duplicate(st.session_state.schedule, entry):
                        st.error("❌ วิชานี้ไม่สามารถบันทึกได้เนื่องจากมีข้อมูลซ้ำซ้อนตรงกันทุกประการ")
                    else:
                        if overlaps:
                            st.warning("⚠️ เวลาเรียนคาบนี้ซ้อนทับกับวิชาอื่นในระบบ:")
                            for o in overlaps:
                                st.write(f"- {o['subject']} ({o['start_time']} - {o['end_time']})")
                        
                        st.session_state.schedule.append(entry)
                        persist_schedule()
                        st.toast("บันทึกวิชาใหม่สำเร็จ!")
                        st.success(f"เพิ่มวิชา **{entry['subject']}** เข้าตารางวัน{entry['day']} สำเร็จแล้ว")


    # ══════════════════════════════════════════════════════════════
    # PAGE 5: Settings
    # ══════════════════════════════════════════════════════════════
    elif st.session_state["current_menu"] == "⚙️ ตั้งค่า":
        page_header("⚙️ ตั้งค่าระบบ", "จัดการรหัสเชื่อมต่อ API และการตั้งเวลาทำงานระบบแจ้งเตือน")

        with st.form("settings"):
            st.subheader("🔑 เชื่อมต่อบัญชี LINE")
            st.info(
                "💡 **ขั้นตอนการเปิดใช้งานแจ้งเตือนผ่าน LINE:**\n"
                "1. ทำการเพิ่มเพื่อนกับบอตระบบแจ้งเตือนส่วนกลางของเรา (LINE Official Account)\n"
                "2. พิมพ์ข้อความใดก็ได้ส่งหาบอต บอตจะตอบข้อความระบุรหัส **LINE User ID** กลับมาให้ทันที\n"
                "3. ทำการคัดลอกรหัสที่ขึ้นต้นด้วยตัว `U` (เช่น `Ua1b2c3d4e5f...`) มากรอกในช่องด้านล่างแล้วกดบันทึก"
            )
            
            current_line_uid = get_user_line_id(st.session_state.user_id)
            line_user_id_input = st.text_input(
                "LINE User ID (UID)",
                value=current_line_uid,
                placeholder="กรอกรหัสที่ได้รับจากบอต เช่น Ua1b2c3d4e5f...",
                help="รหัสเฉพาะตัวของผู้ใช้ที่ระบุปลายทางในการส่งแจ้งเตือนของบอตส่วนกลาง",
            )

            st.subheader("🔔 คอนฟิกตัวตั้งเวลาเปิดกระดิ่งแจ้งเตือน")
            c1, c2 = st.columns(2)
            with c1:
                remind_1day_hour = st.number_input(
                    "เตือนล่วงหน้าช่วงค่ำ (เวลา น. ของวันก่อนหน้าเรียน)",
                    min_value=0, max_value=23, value=int(config.get("remind_1day_hour", 20)),
                )
            with c2:
                remind_hours_before = st.number_input(
                    "ส่งไลน์ส่งซ้ำก่อนคาบเรียนเริ่มจี้ตัว (จำนวนชั่วโมงก่อนเริ่ม)",
                    min_value=0.5, max_value=6.0, value=float(config.get("remind_hours_before", 2.0)), step=0.5,
                )

            saved = st.form_submit_button("💾 บันทึกข้อมูลคอนฟิกทั้งหมดลงไฟล์ระบบ", type="primary", use_container_width=True)
            if saved:
                # บันทึก LINE User ID ลงตาราง users
                update_user_line_id(st.session_state.user_id, line_user_id_input.strip())
                # บันทึกส่วนเสริมอื่นลงตาราง configs
                new_cfg = {
                    "remind_1day_hour": int(remind_1day_hour),
                    "remind_hours_before": float(remind_hours_before),
                }
                save_config_by_user(st.session_state.user_id, new_cfg)
                config.update(new_cfg)
                st.toast("บันทึกคอนฟิกเสร็จสิ้น")
                st.success("ระบบทำการปรับปรุงค่าการเชื่อมต่อเรียบร้อยแล้ว")

        st.divider()
        st.subheader("🧪 โหมดสาธิตการทำงานสำหรับคณะกรรมการสอบ (Presentation Sandbox)")
        st.info("💡 โหมดนี้ออกแบบมาเพื่อจำลองพฤติกรรมการยิงแจ้งเตือนจริงเข้า LINE ผู้ใช้ทันที โดยไม่ต้องรอเวลาจริง เหมาะสำหรับการพรีเซนต์สอบโปรเจกต์")
        
        line_user_id = get_user_line_id(st.session_state.user_id)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🎯 จำลองส่งการเตือนเข้าเรียนวิชาถัดไป", use_container_width=True):
                if not line_user_id:
                    st.error("❌ กรุณากรอกและบันทึก LINE User ID ด้านบนก่อนทดสอบ")
                else:
                    # ค้นหาวิชาถัดไป หรือวิชาจำลองเพื่อความพร้อม
                    today_classes = get_classes_for_day(st.session_state.schedule, today)
                    _, next_cls = get_class_status(today_classes)
                    
                    if not next_cls:
                        # สร้างวิชาจำลองเพื่อให้พรีเซนต์ได้ทุกวันแม้ไม่มีเรียน
                        next_cls = {
                            "subject": "โครงงานคอมพิวเตอร์ (Computer Project Exam)",
                            "start_time": (now + timedelta(hours=1)).strftime("%H:%M"),
                            "end_time": (now + timedelta(hours=3)).strftime("%H:%M"),
                            "room": "ห้องปฏิบัติการ AI (Room 404)"
                        }
                    
                    msg = (
                        f"🚨 [จำลองการเตือนก่อนเริ่มคาบ - คุณ {st.session_state.username}]\n"
                        f"วิชาถัดไปของคุณกำลังจะเริ่มเรียน:\n"
                        f"📖 วิชา: {next_cls['subject']}\n"
                        f"⏰ เวลา: {next_cls['start_time']} น. – {next_cls['end_time']} น.\n"
                        f"📍 ห้องเรียน: {next_cls['room'] or 'ไม่ระบุห้อง'}"
                    )
                    
                    with st.spinner("กำลังจำลองยิงข้อความ..."):
                        ok, res_msg = send_line_notify(line_user_id, msg)
                        if ok:
                            st.success("✅ ส่งการแจ้งเตือนคาบเรียนจำลองเข้า LINE เรียบร้อย!")
                            st.toast("ส่งสำเร็จ! เช็ก LINE ได้เลย", icon="🟢")
                        else:
                            st.error(res_msg)
                            
        with c2:
            if st.button("📚 จำลองส่งการเตือนภาพรวมรายวัน (ล่วงหน้า 1 วัน)", use_container_width=True):
                if not line_user_id:
                    st.error("❌ กรุณากรอกและบันทึก LINE User ID ด้านบนก่อนทดสอบ")
                else:
                    tomorrow_classes = get_classes_for_day(st.session_state.schedule, today_name()) # Use today's classes if tomorrow has none
                    if not tomorrow_classes:
                        # สร้างตารางจำลอง
                        tomorrow_classes = [
                            {"subject": "ความมั่นคงระบบเครือข่าย (Network Security)", "start_time": "09:00", "end_time": "12:00", "room": "LAB 1"},
                            {"subject": "จริยธรรมวิชาชีพคอมพิวเตอร์ (Ethical Tech)", "start_time": "13:00", "end_time": "16:00", "room": "Auditorium"}
                        ]
                    
                    msg = f"📚 [เรียนวันพรุ่งนี้ - คุณ {st.session_state.username}]\nพรุ่งนี้คุณมีตารางเรียนดังนี้ครับ (ข้อมูลจำลองสำหรับการสอบ):\n"
                    for c in sorted(tomorrow_classes, key=lambda x: x["start_time"]):
                        msg += f"• {c['subject']} ({c['start_time']}-{c['end_time']}) ห้อง {c['room'] or 'ไม่ระบุห้อง'}\n"
                        
                    with st.spinner("กำลังจำลองยิงข้อความ..."):
                        ok, res_msg = send_line_notify(line_user_id, msg)
                        if ok:
                            st.success("✅ ส่งการแจ้งเตือนสรุปรายวันจำลองเข้า LINE เรียบร้อย!")
                            st.toast("ส่งสำเร็จ! เช็ก LINE ได้เลย", icon="🟢")
                        else:
                            st.error(res_msg)

        st.divider()

        # เพิ่ม Expander ครอบกลุ่มนี้ทั้งหมดเพื่อซ่อนเมนู
        with st.expander("🛠️ สำหรับผู้พัฒนา / ตั้งค่าขั้นสูง (Advanced Settings)", expanded=False):
            st.subheader("📦 ส่วนจัดการไฟล์และข้อมูลสำรอง")
            c1, c2 = st.columns(2)
            with c1:
                uploaded_backup = st.file_uploader("Import ข้อมูลโครงสร้างแบบ JSON", type=["json"], key="import_json")
                if uploaded_backup:
                    try:
                        imported = json.load(uploaded_backup)
                        if isinstance(imported, list):
                            if st.button("ยืนยันการทำ Import ข้อมูลด่วน"):
                                st.session_state.schedule = imported
                                persist_schedule()
                                st.toast("Import สำเร็จ")
                                st.rerun()
                        else:
                            st.error("โครงสร้างไฟล์อัปโหลดภายนอกต้องอยู่ในรูปแบบอาร์เรย์รายการตารางเท่านั้น")
                    except json.JSONDecodeError:
                        st.error("รูปแบบไฟล์ JSON ชำรุดหรือไม่ถูกต้อง")
        
            with c2:
                st.metric("จำนวนตารางเรียนสะสมปัจจุบันทั้งหมด", len(st.session_state.schedule))
                
                # Backup export download button
                schedule_json_str = json.dumps(st.session_state.schedule, ensure_ascii=False, indent=4)
                st.download_button(
                    label="📥 Export สำรองข้อมูลตารางเรียน (JSON)",
                    data=schedule_json_str,
                    file_name="class_ai_backup.json",
                    mime="application/json",
                    use_container_width=True,
                    key="export_json_backup"  # <-- เพิ่ม key ป้องกัน ID ชนกันตรงนี้ครับ
                )
                if st.button("🗑️ รีเซ็ตลบฐานข้อมูลตารางเรียนทั้งหมด", use_container_width=True, type="primary"):
                    st.session_state.schedule = []
                    persist_schedule()
                    st.toast("รีเซ็ตระบบเรียบร้อย")
                    st.rerun()

    # ══════════════════════════════════════════════════════════════
    # PAGE 6: System Info & Architecture
    # ══════════════════════════════════════════════════════════════
    elif st.session_state["current_menu"] == "ℹ️ ข้อมูลระบบ":
        page_header("ℹ️ ข้อมูลสถาปัตยกรรมระบบ", "โครงสร้างเทคโนโลยีและการเชื่อมโยงการทำงานหลัก")
        
        # Inject Custom Flowchart CSS
        st.markdown(
            """
            <style>
                .flow-container {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    margin: 20px 0;
                    align-items: center;
                    width: 100%;
                }
                .flow-step {
                    display: flex;
                    align-items: center;
                    gap: 20px;
                    width: 100%;
                    max-width: 700px;
                }
                .step-num {
                    width: 46px;
                    height: 46px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 700;
                    font-size: 1.25rem;
                    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
                    flex-shrink: 0;
                    font-family: 'Outfit', sans-serif;
                }
                .step-card {
                    background: rgba(30, 41, 59, 0.25);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 18px;
                    padding: 20px 24px;
                    flex-grow: 1;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                }
                .step-card:hover {
                    transform: translateX(6px);
                    border-color: rgba(99, 102, 241, 0.3);
                    background: rgba(30, 41, 59, 0.35);
                    box-shadow: 0 12px 40px rgba(99, 102, 241, 0.08);
                }
                .step-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                .step-header h4 {
                    margin: 0;
                    font-size: 1.15rem;
                    color: #F8FAFC;
                    font-weight: 600;
                }
                .step-badge {
                    font-size: 10px;
                    font-weight: 700;
                    padding: 3px 10px;
                    border-radius: 99px;
                    letter-spacing: 0.5px;
                    text-transform: uppercase;
                }
                .badge-auth { background: rgba(99, 102, 241, 0.12); color: #A5B4FC; border: 1px solid rgba(99, 102, 241, 0.25); }
                .badge-ai { background: rgba(139, 92, 246, 0.12); color: #C7D2FE; border: 1px solid rgba(139, 92, 246, 0.25); }
                .badge-db { background: rgba(16, 185, 129, 0.12); color: #A7F3D0; border: 1px solid rgba(16, 185, 129, 0.25); }
                .badge-live { background: rgba(239, 68, 68, 0.12); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.25); }
                .badge-hook { background: rgba(245, 158, 11, 0.12); color: #FDE68A; border: 1px solid rgba(245, 158, 11, 0.25); }
                .step-card p {
                    margin: 0;
                    font-size: 0.92rem;
                    color: #94A3B8;
                    line-height: 1.5;
                }
                .flow-arrow {
                    font-size: 1.1rem;
                    color: #475569;
                    margin: 2px 0;
                    animation: bounce 2s infinite alternate;
                }
                @keyframes bounce {
                    0% { transform: translateY(0); }
                    100% { transform: translateY(6px); }
                }
            </style>
            """,
            unsafe_allow_html=True
        )

        tab1, tab2 = st.tabs(["💻 แผนผังการทำงานหน้าบ้าน (Frontend UI)", "⚙️ แผนผังการทำงานหลังบ้าน (Backend Server)"])
        
        with tab1:
            st.markdown(
                """
<div class="flow-container">
<div class="flow-step">
<div class="step-num">1</div>
<div class="step-card">
<div class="step-header">
<h4>🔐 ล็อกอินเข้าสู่ระบบ (User Session)</h4>
<span class="step-badge badge-auth">Security</span>
</div>
<p>ผู้ใช้งานเข้าสู่หน้าเว็บ สมัครสมาชิกและล็อกอินผ่านระบบความปลอดภัยด้วยการแฮชรหัสผ่าน แยกเซสชันข้อมูลผู้ใช้งานแต่ละคนแยกขาดจากกัน</p>
</div>
</div>
<div class="flow-arrow">▼</div>
<div class="flow-step">
<div class="step-num">2</div>
<div class="step-card">
<div class="step-header">
<h4>📸 สแกนรูปภาพตารางเรียนด้วย AI</h4>
<span class="step-badge badge-ai">Gemini AI</span>
</div>
<p>ผู้ใช้อัปโหลดรูปภาพตารางเรียน ระบบส่งให้ Google Gemini Flash AI (คีย์ส่วนกลาง) สแกนแปลงรูปภาพเป็นข้อมูลวิชาเรียนโครงสร้าง JSON</p>
</div>
</div>
<div class="flow-arrow">▼</div>
<div class="flow-step">
<div class="step-num">3</div>
<div class="step-card">
<div class="step-header">
<h4>📝 ยืนยันข้อมูลตารางเรียน (Review & Save)</h4>
<span class="step-badge badge-db">Database</span>
</div>
<p>ระบบนำข้อมูลที่สแกนมาแสดงพรีวิวให้ผู้ใช้ตรวจสอบ แก้ไขคาบเวลาห้องเรียนเพิ่มเติมได้อิสระ ก่อนกดยืนยันจัดเก็บเข้าฐานข้อมูล SQLite</p>
</div>
</div>
<div class="flow-arrow">▼</div>
<div class="flow-step">
<div class="step-num">4</div>
<div class="step-card">
<div class="step-header">
<h4>📊 ติดตามเวลาเรียน (Dashboard Monitor)</h4>
<span class="step-badge badge-live">Live UI</span>
</div>
<p>แดชบอร์ดหลักแสดงเวลานับถอยหลัง คาบเรียนปัจจุบันที่กำลังเรียน คาบเรียนถัดไป พร้อมกราฟแสดงชั่วโมงเรียนสะสมสรุปรายวัน</p>
</div>
</div>
</div>
""",
                unsafe_allow_html=True
            )
            
        with tab2:
            st.markdown(
                """
<div class="flow-container">
<div class="flow-step">
<div class="step-num">1</div>
<div class="step-card">
<div class="step-header">
<h4>📡 รับสัญญาณ LINE Webhook (พอร์ต 8000)</h4>
<span class="step-badge badge-hook">Webhook</span>
</div>
<p>ระบบเปิดมินิเซิร์ฟเวอร์ดักสัญญาณ เมื่อผู้ใช้แอดไลน์หรือส่งแชทหาบอทส่วนกลาง ระบบจะตรวจความเที่ยงตรงและตอบกลับเป็นรหัส User ID (UID) ส่วนตัว</p>
</div>
</div>
<div class="flow-arrow">▼</div>
<div class="flow-step">
<div class="step-num">2</div>
<div class="step-card">
<div class="step-header">
<h4>⏰ ตัวตรวจตารางเรียน (Scheduler Daemon)</h4>
<span class="step-badge badge-db">Time Loop</span>
</div>
<p>ตัวจัดการแจ้งเตือนวนตรวจสอบเวลาฐานข้อมูล SQLite ทุก 30 วินาที คำนวณเวลาเริ่มเรียนตามโซนเวลาประเทศไทย UTC+7 (ICT) ตลอด 24 ชม.</p>
</div>
</div>
<div class="flow-arrow">▼</div>
<div class="flow-step">
<div class="step-num">3</div>
<div class="step-card">
<div class="step-header">
<h4>📚 ส่งแจ้งเตือนตารางวันพรุ่งนี้ (1-Day Ahead)</h4>
<span class="step-badge badge-auth">Push Notify</span>
</div>
<p>เมื่อถึงเวลาค่ำที่กำหนด (ค่าเริ่มต้น 20.00 น.) ระบบจะดึงตารางของวันพรุ่งนี้ทั้งหมด ประกอบข้อความเป็นสรุปรายวัน ยิงเตือนเข้า LINE</p>
</div>
</div>
<div class="flow-arrow">▼</div>
<div class="flow-step">
<div class="step-num">4</div>
<div class="step-card">
<div class="step-header">
<h4>🚨 แจ้งเตือนก่อนเริ่มเรียนจริง (2-Hour Alert)</h4>
<span class="step-badge badge-live">Critical Alert</span>
</div>
<p>ก่อนถึงเวลาเข้าเรียนรายวิชาจริง 2 ชั่วโมง บอทหลังบ้านจะสั่งยิงการเตือนระบุวิชา เวลาเรียน และห้องเรียนตรงไปยังโทรศัพท์ผู้ใช้ทันที</p>
</div>
</div>
</div>
""",
                unsafe_allow_html=True
            )
            
        st.divider()
        
        st.markdown(
            """
            ### 📦 รายละเอียดส่วนประกอบหลักของระบบ
            
            1. **💻 Streamlit Web Application (`app.py`)**
               - หน้าเว็บติดต่อผู้ใช้งานแบบความเร็วสูง ทำหน้าที่ให้ผู้ใช้เข้ามาสมัครสมาชิก ล็อกอิน จัดการตารางเรียน และตั้งค่ารหัส LINE ID บัญชี
               
            2. **💾 SQLite Database (`class_ai_system.db`)**
               - ฐานข้อมูลหลักที่เก็บข้อมูลผู้ใช้ตารางแฮช (`users`), ข้อมูลคาบวิชาเรียน (`schedules`), และข้อมูลคอนฟิกแจ้งเตือน (`configs`) ของทุกคนอย่างเป็นสัดส่วน ปลอดภัย
               
            3. **🤖 Google Gemini AI Scanner (`utils/ai_scanner.py`)**
               - ตัวช่วยวิเคราะห์เชิงลึกรูปภาพตารางเรียน ดึงข้อความรายวิชาออกมาและแปลงเป็นรูปแบบโครงสร้างข้อมูลดิจิทัล JSON นำเข้าตารางทันที
               
            4. **⚙️ Background Scheduler & Webhook Server (`worker.py`)**
               - **Scheduler:** เทรดทำหน้าที่ตรวจสอบเงื่อนไขเวลาเรียนจริงของผู้ใช้ เพื่อเตรียมส่งแจ้งเตือน
               - **Webhook Server:** มินิเซิร์ฟเวอร์รันอยู่เบื้องหลัง (พอร์ต 8000) คอยรับสัญญาณจาก LINE Developers และตอบกลับ ID ทันทีแบบเรียลไทม์
            """,
            unsafe_allow_html=True
        )