import sqlite3
import json
import bcrypt

DB_PATH = "class_ai_system.db"

def dict_factory(cursor, row):
    """แปลงผลลัพธ์จาก SQL ให้กลายเป็น Dict เพื่อให้เข้ากับระบบเดิมของแอป"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def init_db():
    """สร้างฐานข้อมูลและตารางต่างๆ หากยังไม่มีในระบบ (ทำงานอัตโนมัติเมื่อรันแอปครั้งแรก)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. ตารางเก็บข้อมูลผู้ใช้ (Users)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        line_user_id TEXT
    )
    """)
    
    # 2. ตารางเก็บตารางเรียน (Schedules) ผูกกับ user_id ของผู้ใช้คนนั้นๆ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        room TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    # 3. ตารางเก็บข้อมูลการตั้งค่า API และเวลาแจ้งเตือน (Configs) แยกเป็นรายบุคคล
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configs (
        user_id INTEGER PRIMARY KEY,
        config_data TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)
    
    # ทำการอัปเกรดตารางผู้ใช้หากคอลัมน์ line_user_id ยังไม่มี (Migration)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN line_user_id TEXT")
    except sqlite3.OperationalError:
        pass  # คอลัมน์มีอยู่แล้ว
        
    conn.commit()
    conn.close()

# เรียกฟังก์ชันสร้างตารางทันทีเมื่อไฟล์นี้ถูก Import เข้าใช้งาน
init_db()


# ── 🔐 ระบบความปลอดภัยและจัดการสมาชิก (Authentication) ──────────────────

def register_user(username, password) -> bool:
    """สมัครสมาชิกใหม่พร้อมแฮชรหัสผ่านเพื่อความปลอดภัย"""
    username = username.strip().lower()
    if not username or not password:
        return False
    
    # แฮชรหัสผ่านด้วย bcrypt ก่อนบันทึก ป้องกันข้อมูลรั่วไหล
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
        user_id = cursor.lastrowid
        
        # ตั้งค่าตั้งค่าเบื้องต้นให้กับสมาชิกที่ลงทะเบียนเสร็จทันที
        default_cfg = {
            "line_token": "",
            "channel_access_token": "",
            "gemini_key": "",
            "remind_1day_hour": 20,
            "remind_hours_before": 2.0
        }
        cursor.execute("INSERT INTO configs (user_id, config_data) VALUES (?, ?)", (user_id, json.dumps(default_cfg)))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # คืนค่า False หากชื่อผู้ใช้งานซ้ำในฐานข้อมูล
    finally:
        conn.close()


def authenticate_user(username, password):
    """ตรวจสอบการเข้าสู่ระบบ คืนค่า tuple (user_id, username) หรือ None หากรหัสผ่านผิด"""
    username = username.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        user_id, password_hash = row
        # ตรวจสอบรหัสผ่านว่าตรงกับที่แฮชเก็บไว้หรือไม่
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return user_id, username
    return None


# ── 📅 ระบบจัดการตารางเรียนตามรายบุคคล (User-Specific Schedules) ──────────

def load_schedule_by_user(user_id: int) -> list:
    """ดึงข้อมูลตารางเรียนทั้งหมดที่เชื่อมโยงกับ user_id ออกมาในรูป List of Dicts"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject, day, start_time, end_time, room FROM schedules WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_schedule_by_user(user_id: int, schedule_list: list):
    """ลบและบันทึกตารางเรียนใหม่ทดแทนของเดิมทั้งหมดสำหรับผู้ใช้เจาะจงรายคน"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM schedules WHERE user_id = ?", (user_id,))
        for item in schedule_list:
            cursor.execute("""
                INSERT INTO schedules (user_id, subject, day, start_time, end_time, room)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, item['subject'], item['day'], item['start_time'], item['end_time'], item.get('room', '')))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ── ⚙️ ระบบจัดการตั้งค่าแอปแยกรายบุคคล (User-Specific Configurations) ──────

def load_config_by_user(user_id: int) -> dict:
    """ดึงค่าคอนฟิกส่วนบุคคล หากยังไม่มีจะสร้างเป็นค่าเริ่มต้นให้ทันที"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT config_data FROM configs WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return {
        "line_token": "",
        "channel_access_token": "",
        "gemini_key": "",
        "remind_1day_hour": 20,
        "remind_hours_before": 2.0
    }


def save_config_by_user(user_id: int, config_dict: dict):
    """บันทึกข้อมูลการตั้งค่า API และข้อความแจ้งเตือนใหม่ลงใน ID ของตัวเอง"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configs (user_id, config_data)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET config_data = excluded.config_data
    """, (user_id, json.dumps(config_dict, ensure_ascii=False)))
    conn.commit()
    conn.close()

def update_user_line_id(user_id, line_id):
    """ฟังก์ชันสำหรับบันทึกหรืออัปเดตรหัส LINE User ID ลงฐานข้อมูล"""
    conn = sqlite3.connect("class_ai_system.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET line_user_id = ? 
        WHERE id = ?
    """, (line_id, user_id))
    conn.commit()
    conn.close()

def get_user_line_id(user_id):
    """ฟังก์ชันดึงรหัส LINE User ID ของผู้ใช้ปัจจุบันออกมาใช้งาน"""
    conn = sqlite3.connect("class_ai_system.db")
    cursor = conn.cursor()
    cursor.execute("SELECT line_user_id FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""