import time
import json
import os
import sqlite3
import threading
import requests
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

import functools
print = functools.partial(print, flush=True)

# Import LINE notification function and token from utils
from utils.notifications import send_class_reminder, CENTRAL_CHANNEL_ACCESS_TOKEN
from utils.schedule import get_bangkok_time

DB_PATH = "class_ai_system.db"
DAYS_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]

# ── 📡 LINE Webhook Server ──────────────────────────────────────────

class LineWebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP request logging in console
        pass

    def do_POST(self):
        try:
            with open("webhook_access.log", "a", encoding="utf-8") as f:
                f.write(f"📥 POST from {self.client_address} at {datetime.now()} | Path: {self.path}\n")
        except Exception:
            pass
        print(f"\n📥 [Webhook] ได้รับการติดต่อแบบ POST จาก {self.client_address}")
        # Read the POST request body
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                print("⚠️ [Webhook] Content-Length เป็น 0 (ข้ามการทำงาน)")
                self.send_response(400)
                self.end_headers()
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            events = data.get('events', [])
            print(f"📦 [Webhook] ได้รับอีเวนต์ย่อยจำนวน {len(events)} รายการ")
            
            for event in events:
                event_type = event.get('type')
                reply_token = event.get('replyToken')
                source = event.get('source', {})
                user_id = source.get('userId')
                
                print(f"   • อีเวนต์ประเภท: {event_type} | User ID: {user_id}")
                
                # Check if it's a message event or a follow (add friend) event
                if (event_type in ('message', 'follow')) and reply_token and user_id:
                    # Compose the response message containing the LINE User ID
                    reply_text = (
                        f"🎓 สวัสดีครับ! ยินดีต้อนรับสู่ระบบ Class AI\n\n"
                        f"นี่คือ LINE User ID (UID) ของคุณ สำหรับนำไปใส่ในแอปพลิเคชัน:\n\n"
                        f"{user_id}\n\n"
                        f"👉 กรุณาคัดลอกรหัส (UID) ด้านบนทั้งหมด แล้วนำไปวางในหน้า '⚙️ ตั้งค่า' ของระบบ ในหัวข้อ 'LINE User ID' ได้เลยครับ! 🔔"
                    )
                    self.reply_line(reply_token, reply_text)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            print(f"❌ [Webhook] เกิดข้อผิดพลาดในการรับสัญญาณ: {e}")
            self.send_response(500)
            self.end_headers()

    def reply_line(self, reply_token, text):
        if not CENTRAL_CHANNEL_ACCESS_TOKEN or CENTRAL_CHANNEL_ACCESS_TOKEN == "ใส่_TOKEN_ของบอทคุณตรงนี้":
            print("⚠️ [Webhook] ยังไม่ได้ตั้งค่าคีย์โทเค็นใน utils/notifications.py")
            return False
            
        print(f"📤 [Webhook] กำลังตอบกลับไปยัง replyToken: {reply_token[:10]}...")
        url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CENTRAL_CHANNEL_ACCESS_TOKEN}"
        }
        payload = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"   Response status จาก LINE API: {res.status_code}")
            if res.status_code != 200:
                print(f"   รายละเอียดข้อผิดพลาด: {res.text}")
            return res.status_code == 200
        except Exception as e:
            print(f"❌ [Webhook] มีข้อผิดพลาดระหว่างยิงตอบกลับ LINE: {e}")
            return False

def run_webhook_server(port=8000):
    try:
        server = HTTPServer(('0.0.0.0', port), LineWebhookHandler)
        print(f"📡 LINE Webhook Server กำลังทำงานที่พอร์ต {port}...")
        server.serve_forever()
    except Exception as e:
        print(f"❌ ไม่สามารถสตาร์ท Webhook Server ได้: {e}")

# ── 📅 Helper Functions for SQLite ────────────────────────────────────

def get_active_users_with_line():
    """ดึงรายชื่อผู้ใช้ทั้งหมดที่มีการระบุ LINE User ID แล้ว"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, line_user_id FROM users WHERE line_user_id IS NOT NULL AND line_user_id != ''")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "username": r[1], "line_user_id": r[2]} for r in rows]
    except Exception as e:
        print(f"❌ Database error in get_active_users_with_line: {e}")
        return []

def get_user_schedule(user_id):
    """ดึงตารางเรียนของผู้ใช้เฉพาะเจาะจง"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT subject, day, start_time, end_time, room FROM schedules WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{"subject": r[0], "day": r[1], "start_time": r[2], "end_time": r[3], "room": r[4]} for r in rows]
    except Exception as e:
        print(f"❌ Database error in get_user_schedule: {e}")
        return []

def get_user_config(user_id):
    """ดึงข้อมูลตั้งค่าการแจ้งเตือนของผู้ใช้ หากไม่มีให้ใช้ค่าเริ่มต้น"""
    default_config = {
        "remind_1day_hour": 20,
        "remind_hours_before": 2.0
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT config_data FROM configs WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            user_cfg = json.loads(row[0])
            default_config.update(user_cfg)
    except Exception as e:
        print(f"❌ Database error in get_user_config: {e}")
    return default_config


# ── 🏃 Main Scheduler Process ────────────────────────────────────────

print("🤖 Class Reminder Worker & Webhook Server กำลังเตรียมรันระบบ...")

# เริ่มรัน Webhook Server ใน Background Thread (พอร์ต 8000)
webhook_thread = threading.Thread(target=run_webhook_server, args=(8000,), daemon=True)
webhook_thread.start()

# ชุดข้อมูลป้องกันการส่งแจ้งเตือนซ้ำ
already_sent_1day = set()       # เก็บค่ารูปแบบ "user_id_YYYY-MM-DD"
already_sent_before = set()     # เก็บค่ารูปแบบ "user_id_subject_start_time_YYYY-MM-DD"

print("⏰ Scheduler Loop ทำงานเรียบร้อยแล้ว (ตรวจสอบทุก 30 วินาที)")

while True:
    try:
        now = get_bangkok_time()
        current_day = DAYS_TH[now.weekday()]
        tomorrow = now + timedelta(days=1)
        tomorrow_day = DAYS_TH[tomorrow.weekday()]
        tomorrow_date_str = tomorrow.strftime("%Y-%m-%d")
        today_date_str = now.strftime("%Y-%m-%d")

        # ล้างประวัติการแจ้งเตือนตอนเที่ยงคืน
        if now.hour == 0 and now.minute == 0 and now.second < 35:
            already_sent_1day.clear()
            already_sent_before.clear()
            print(f"🧹 ล้างประวัติการแจ้งเตือนในวันปัจจุบันเรียบร้อยแล้ว ณ {now}")

        # ดึงรายชื่อผู้ใช้ที่ผูกบัญชี LINE ไว้
        users = get_active_users_with_line()

        for user in users:
            user_id = user["id"]
            username = user["username"]
            line_user_id = user["line_user_id"]
            
            # โหลดตารางเรียนและการตั้งค่าของผู้ใช้คนนั้นๆ
            schedule = get_user_schedule(user_id)
            config = get_user_config(user_id)
            
            remind_hour = int(config.get("remind_1day_hour", 20))
            remind_before = float(config.get("remind_hours_before", 2.0))
            
            # หน้าต่างเวลาสำหรับการเตือนจี้ตัวก่อนเรียน (ค่า default 2 ชม. คือช่วง 1.5 - 2 ชม.)
            remind_window_min = remind_before - 0.5
            remind_window_max = remind_before

            # 1. การแจ้งเตือนล่วงหน้า 1 วัน (ช่วงเวลาค่ำ)
            if now.hour == remind_hour and now.minute == 0:
                sent_key = f"{user_id}_{tomorrow_date_str}"
                if sent_key not in already_sent_1day:
                    tomorrow_classes = [c for c in schedule if c["day"] == tomorrow_day]
                    if tomorrow_classes:
                        msg = f"📚 [เรียนพรุ่งนี้ - คุณ {username}]\nพรุ่งนี้ (วัน{tomorrow_day}) คุณมีตารางเรียนดังนี้ครับ:\n"
                        for c in sorted(tomorrow_classes, key=lambda x: x["start_time"]):
                            msg += f"• {c['subject']} ({c['start_time']}-{c['end_time']}) ห้อง {c['room'] or 'ไม่ระบุห้อง'}\n"
                        
                        success = send_class_reminder(line_user_id, msg)
                        if success:
                            already_sent_1day.add(sent_key)
                            print(f"📧 ส่งการแจ้งเตือนล่วงหน้า 1 วัน ให้คุณ {username} เรียบร้อย")

            # 2. การแจ้งเตือนก่อนเรียนจริง (เช่น ล่วงหน้า 2 ชั่วโมง)
            for c in schedule:
                if c["day"] != current_day:
                    continue
                    
                # คำนวณเวลาเริ่มเรียนของวิชานั้นในวันนี้
                try:
                    class_dt = datetime.strptime(f"{today_date_str} {c['start_time']}", "%Y-%m-%d %H:%M")
                    diff_h = (class_dt - now).total_seconds() / 3600
                except Exception as e:
                    print(f"⚠️ แปลงค่าเวลาของวิชาผิดพลาด ({c['subject']}): {e}")
                    continue
                
                # เช็กว่าเวลาปัจจุบันอยู่ในหน้าต่างการแจ้งเตือนหรือไม่
                if remind_window_min <= diff_h <= remind_window_max:
                    sent_key = f"{user_id}_{c['subject']}_{c['start_time']}_{today_date_str}"
                    if sent_key not in already_sent_before:
                        msg = (
                            f"🚨 [เตรียมตัวเข้าเรียน - คุณ {username}]\n"
                            f"อีกไม่นานนี้ คุณมีเรียนวิชา:\n"
                            f"📖 วิชา: {c['subject']}\n"
                            f"⏰ เริ่มเวลา: {c['start_time']} น. - {c['end_time']} น.\n"
                            f"📍 ห้องเรียน: {c['room'] or 'ไม่ระบุห้อง'}"
                        )
                        success = send_class_reminder(line_user_id, msg)
                        if success:
                            already_sent_before.add(sent_key)
                            print(f"📧 ส่งการแจ้งเตือนก่อนเริ่มคาบวิชา {c['subject']} ให้คุณ {username} เรียบร้อย")

    except Exception as e:
        print(f"❌ Error in main scheduler loop: {e}")
        
    time.sleep(30)