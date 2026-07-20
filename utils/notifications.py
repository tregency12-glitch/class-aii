import requests

# 🚨 ใส่ Channel Access Token ของบอทส่วนกลางที่คุณสมัครไว้ที่นี่ที่เดียว
CENTRAL_CHANNEL_ACCESS_TOKEN = "zSkZH3AkdjBlJrx1xol1Vgcm4W/ZujOoNUKXQ3lo0iblAJPGqNBg2PjC7tRWA39QAOt6H70dfrvgi6jOuGsS7+T4C8exs8uKKrKCKLiuzylQH4b56O77Oqhhk2+S4CQ/395ZoRjSvL3syVZJkN08ewdB04t89/1O/w1cDnyilFU="

def send_class_reminder(line_user_id, message_text):
    """
    ฟังก์ชันส่งข้อความแจ้งเตือนไปยัง LINE User ID ปลายทาง
    """
    if not line_user_id:
        return False  # ถ้าไม่มี ID ไลน์ ให้ข้ามการส่งทันทีเพื่อไม่ให้บอตเออเรอร์

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CENTRAL_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": line_user_id,  # ยิงตรงหาผู้ใช้คนนี้
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message to LINE: {e}")
        return False

def send_line_notify(line_user_id, message_text):
    """
    ส่งข้อความผ่าน LINE Official Account (Push Message) ไปยัง line_user_id โดยตรง
    คืนค่า (success_bool, message_str)
    """
    if not line_user_id:
        return False, "❌ ไม่พบ LINE User ID ในระบบ"
        
    if not CENTRAL_CHANNEL_ACCESS_TOKEN or CENTRAL_CHANNEL_ACCESS_TOKEN == "CENTRAL_CHANNEL_ACCESS_TOKEN":
        return False, "❌ ระบบหลังบ้านยังไม่ได้ตั้งค่าคีย์บอทส่วนกลาง (CENTRAL_CHANNEL_ACCESS_TOKEN)"
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CENTRAL_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": line_user_id,
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "✅ ส่งข้อความทดสอบสำเร็จ! กรุณาตรวจสอบโทรศัพท์มือถือที่ผูกกับ LINE Bot"
        else:
            return False, f"❌ ส่งไม่สำเร็จ (HTTP {response.status_code}): {response.text}"
    except Exception as e:
        return False, f"❌ เกิดข้อผิดพลาดทางเทคนิค: {str(e)}"