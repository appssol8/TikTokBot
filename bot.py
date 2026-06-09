import os
import json
import time
import telebot
import yt_dlp
import whisper

# --- الإعدادات ---
# سيتم جلبها من GitHub Secrets لاحقاً
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# --- قائمة حسابات تيك توك (عدلها كما تريد لاحقاً) ---
TARGET_ACCOUNTS = [
    "appssol"
# ---   , "username2",--- # استبدل هذا بحساب آخر
# ---    "username3" --- # استبدل هذا بحساب آخر
]

# تحميل نموذج الذكاء الاصطناعي
print("Loading Whisper model...")
model = whisper.load_model("base")

# إعداد البوت
bot = telebot.TeleBot(BOT_TOKEN)

# ملف الحالة (لحفظ المعرفات حتى لا تتكرر)
STATE_FILE = "state.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def process_account(username, state_data):
    print(f"Checking: @{username}")
    url = f"https://www.tiktok.com/@{username}"
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'playlistend': 2,  # فحص آخر فيديوين فقط لتوفير الوقت
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info and info['entries']:
                for video in info['entries']:
                    vid_id = video['id']
                    
                    # التحقق إذا كان الفيديو هو الآخر وتم إرساله سابقاً
                    # نحن نهتم بآخر فيديو فقط، لذا نتحقق من الحالة المحفوظة
                    if state_data.get(username) == vid_id:
                        continue # تم الإرسال سابقاً، تخطي
                    
                    # فيديو جديد!
                    print(f"New video found for {username}: {vid_id}")
                    video_url = video.get('url') or f"https://www.tiktok.com/@{username}/video/{vid_id}"
                    
                    # تحميل، تفريغ، إرسال
                    success = download_and_send(video_url, vid_id, username)
                    
                    if success:
                        # تحديث الحالة بعد الإرسال بنجاح
                        state_data[username] = vid_id
                        # حفظ فوري
                        save_state(state_data)
                        time.sleep(5) # انتظار بسيط بين الفيديوهات

    except Exception as e:
        print(f"Error checking {username}: {e}")

def download_and_send(url, vid_id, username):
    filename = f"{vid_id}.mp4"
    try:
        # تحميل الفيديو
        ydl_opts = {'outtmpl': filename, 'format': 'mp4', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # تفريغ النص
        print(f"Transcribing {vid_id}...")
        result = model.transcribe(filename, language='ar')
        text = result["text"]
        
        # إرسال للتيليجرام
        caption = f"🎬 جديد: @{username}\n\n📝 النص:\n{text}"
        
        # التيليجران يقبل كابتشن حتى 1024 حرف، نقطع الزيادة لو موجود
        with open(filename, 'rb') as video_file:
            bot.send_video(CHAT_ID, video_file, caption=caption[:1024])
        
        print("Sent successfully!")
        
        # حذف الملف لتوفير المساحة
        if os.path.exists(filename):
            os.remove(filename)
            
        return True
    except Exception as e:
        print(f"Failed to process {vid_id}: {e}")
        return False

# --- نقطة البداية ---
if __name__ == "__main__":
    print("Bot started scheduled run...")
    
    # تحميل الحالة السابقة
    current_state = load_state()
    
    for acc in TARGET_ACCOUNTS:
        process_account(acc, current_state)
        time.sleep(10) # راحة 10 ثواني بين كل حساب والآخر لتخفيف الضغط
    
    # حفظ نهائي للحالة (في حال فات شيء)
    save_state(current_state)
    print("Job finished.")
