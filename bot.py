# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
import aiosqlite
import json
import httpx
import asyncio
import os

# --- Configuration ---
# ... (Configuration remains the same) ...
api_id = 18377832
api_hash = "ed8556c450c6d0fd68912423325dd09c"
session_name = "my_ai_multi_model"
admin_id = 7094106651
json_file = 'users_started.json'

# --- Bot State ---
# ... (Bot state remains the same) ...
client = TelegramClient(session_name, api_id, api_hash)
bot_active = True
user_states = {}

# --- Constants ---
# ... (Constants remain the same) ...
languages = [
    "Laravel", "Python", "Java", "JavaScript", "C#", "C++", "C",
    "Swift", "Golang", "Rust", "Kotlin", "TypeScript", "PhP"
]

ext_map = {
    "Python": "py", "Java": "java", "JavaScript": "js", "C#": "cs", "C++": "cpp", "C": "c",
    "Swift": "swift", "Golang": "go", "Rust": "rs", "Kotlin": "kt", "TypeScript": "ts",
    "PhP": "php", "Laravel": "php"
}

AI_MODELS = {
    "gpt": "GPT (Binjie)",
    "gemini": "Gemini 2.0 Flash"
}

GPT_API_URL = "https://api.binjie.fun/api/generateStream"
GEMINI_API_URL = "https://gem-ehsan.vercel.app/gemini/chat"
GEMINI_MODEL_ID = "2"


# --- JSON User Tracking ---
# ... (load_started_users, save_started_users, add_started_user, get_started_users_list functions remain the same) ...
def load_started_users():
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_started_users(users):
    with open(json_file, 'w', encoding='utf-8') as file:
        json.dump(users, file, ensure_ascii=False, indent=4)

def add_started_user(user_id):
    users = load_started_users()
    if user_id not in users:
        users.append(user_id)
        save_started_users(users)

def get_started_users_list():
    return load_started_users()


# --- SQLite User Tracking ---
# ... (init_db, add_user_to_db functions remain the same) ...
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        await db.commit()

async def add_user_to_db(user_id):
    try:
        async with aiosqlite.connect("users.db", timeout=10) as db: # Added timeout
            await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            await db.commit()
    except aiosqlite.Error as e:
        print(f"Database error adding user {user_id}: {e}")


# --- Event Handlers ---
# ... (start, return_to_main_menu, choose_ai_model, handle_ai_model_selection, handle_language_selection remain the same) ...

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not bot_active and event.sender_id != admin_id:
        return
    user_id = event.sender_id
    await add_user_to_db(user_id)
    add_started_user(user_id)
    user_states.pop(user_id, None)
    await event.respond(
        "**سلام، چطوری میتونم کمکت کنم؟**",
        buttons=[
            [Button.inline("🧬 کد نویسی", b"select_ai")],
            [Button.inline("📚 راهنما", b"help")],
            [Button.url("🧑‍💻 ارتباط با توسعه دهنده", "https://t.me/n6xel")]
        ]
    )

@client.on(events.CallbackQuery(data=b"main_menu"))
async def return_to_main_menu(event):
    user_id = event.sender_id
    user_states.pop(user_id, None)
    await event.edit(
        "**سلام، چطوری میتونم کمکت کنم؟**",
        buttons=[
            [Button.inline("🧬 کد نویسی", b"select_ai")],
            [Button.inline("📚 راهنما", b"help")],
            [Button.url("🧑‍💻 ارتباط با توسعه دهنده", "https://t.me/n6xel")]
        ]
    )

@client.on(events.CallbackQuery(data=b'select_ai'))
async def choose_ai_model(event):
    if not bot_active and event.sender_id != admin_id:
        await event.answer("ربات در حال حاضر غیرفعال است.", alert=True)
        return
    user_id = event.sender_id
    user_states.pop(user_id, None)
    ai_buttons = [
        Button.inline(name, f"model_{key}".encode('utf-8'))
        for key, name in AI_MODELS.items()
    ]
    rows = []
    for i in range(0, len(ai_buttons), 2):
        rows.append(ai_buttons[i:i+2])
    rows.append([Button.inline("🔙 برگشت به منوی اصلی", b"main_menu")])
    await event.edit("**لطفا مدل هوش مصنوعی را انتخاب کنید:**", buttons=rows)

@client.on(events.CallbackQuery(pattern=b'model_(.*)'))
async def handle_ai_model_selection(event):
    if not bot_active and event.sender_id != admin_id:
        await event.answer("ربات در حال حاضر غیرفعال است.", alert=True)
        return
    user_id = event.sender_id
    try:
        model_key = event.pattern_match.group(1).decode('utf-8')
    except Exception as e:
        print(f"Error decoding model key: {e}")
        await event.answer("خطا در پردازش انتخاب.", alert=True)
        return
    if model_key not in AI_MODELS:
        await event.answer("مدل نامعتبر است.", alert=True)
        return
    user_states[user_id] = {"model": model_key}
    lang_buttons = [Button.inline(lang, f"lang_{lang}".encode('utf-8')) for lang in languages]
    rows = []
    for i in range(0, len(lang_buttons), 2):
        rows.append(lang_buttons[i:i+2])
    rows.append([Button.inline("🔙 برگشت به انتخاب مدل", b"select_ai")])
    await event.edit(
        f"**مدل انتخاب شده: {AI_MODELS[model_key]}**\n\n**لطفاً زبان برنامه‌نویسی را انتخاب کنید:**",
        buttons=rows
    )

@client.on(events.CallbackQuery(pattern=b'lang_(.*)'))
async def handle_language_selection(event):
    if not bot_active and event.sender_id != admin_id:
        await event.answer("ربات در حال حاضر غیرفعال است.", alert=True)
        return
    user_id = event.sender_id
    try:
        lang = event.pattern_match.group(1).decode('utf-8')
    except Exception as e:
        print(f"Error decoding language: {e}")
        await event.answer("خطا در پردازش زبان.", alert=True)
        return
    if lang not in languages:
        await event.answer("زبان نامعتبر است.", alert=True)
        return
    if user_id not in user_states or "model" not in user_states[user_id]:
        await event.edit("**خطا: ابتدا باید مدل هوش مصنوعی را انتخاب کنید.**", buttons=[Button.inline("انتخاب مدل", b"select_ai")])
        return
    user_states[user_id]["language"] = lang
    selected_model_key = user_states[user_id]["model"]
    selected_model_name = AI_MODELS.get(selected_model_key, "ناشناخته")
    await event.edit(
        f"**مدل: {selected_model_name}**\n"
        f"**زبان: {lang}**\n\n"
        "**سوالت رو بپرس تا کدشو بنویسم.**",
        buttons=[
            Button.inline("🔙 برگشت به انتخاب زبان", f"model_{selected_model_key}".encode('utf-8'))
        ]
    )


async def is_code_related(text, user_id):
    check_prompt = f'Is the following message a valid request for generating programming code? Answer only with "yes" or "no".\n\n"{text}"'
    try:
        print(f"Checking relevance for user {user_id}: {text[:50]}...")
        reply = await call_gpt_api(check_prompt, f"validator-{user_id}")
        print(f"Relevance check reply: {reply}")
        return "yes" in reply.lower()
    except Exception as e:
        print(f"Error during code relevance check: {e}")
        return False


@client.on(events.NewMessage)
async def handle_message(event):
    if event.text.startswith('/') or not event.is_private:
        if event.sender_id == admin_id and event.text.startswith('/'):
             return
        elif not event.text.startswith('/'):
            pass
        else:
             return

    if not bot_active and event.sender_id != admin_id:
        return

    user_id = event.sender_id
    chat_id = event.chat_id
    user_input = event.text.strip()

    if user_id in user_states and "model" in user_states[user_id] and "language" in user_states[user_id]:
        lang = user_states[user_id]["language"]
        model = user_states[user_id]["model"]
        model_name = AI_MODELS.get(model, "AI")

        async with client.action(chat_id, "typing"):
            is_valid = await is_code_related(user_input, user_id)

        if not is_valid:
            await event.respond("**متاسفم، به نظر نمی‌رسه این یک درخواست معتبر برای نوشتن کد باشه. لطفا درخواست مربوط به برنامه‌نویسی رو مطرح کن.**")
            if user_id in user_states: del user_states[user_id]
            return

        prompt = f"Please provide only the {lang} code for the following request, without any explanation before or after the code block:\n\n{user_input}"
        processing_msg = await event.respond(f"**در حال پردازش درخواست شما با {model_name} برای زبان {lang}... لطفاً صبر کنید.**")

        response = None
        async with client.action(chat_id, "typing"):
            try:
                if model == "gemini":
                    response = await call_gemini_api(prompt, user_id)
                elif model == "gpt":
                    gpt_prompt = f"{lang}: {user_input}. Only provide the code block as output."
                    response = await call_gpt_api(gpt_prompt, user_id)
                else:
                    response = "خطا: مدل هوش مصنوعی انتخاب شده معتبر نیست."
            except Exception as e:
                response = f"متاسفانه در تولید کد خطایی رخ داد: {e}"
                print(f"Error during API call for user {user_id}: {e}")

        if response:
            response = response.strip().strip('`')
            if response.lower().startswith(lang.lower()):
                 response = response[len(lang):].strip()

            try:
                # --- Button Definitions ---
                back_to_lang_button = Button.inline(
                    "🔙 بازگشت به زبان‌ها",
                    f"model_{model}".encode('utf-8')
                )
                new_code_button = Button.inline(
                    "🔄 کد جدید از همین زبان",
                    f"newcode_{model}_{lang}".encode('utf-8') # Include model and lang
                )

                if len(response) > 4000:
                    ext = ext_map.get(lang, "txt")
                    filename = f"code_{user_id}_{lang.lower()}.{ext}"
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(response)
                        # Send file with buttons
                        await client.send_file(
                            event.chat_id,
                            filename,
                            caption=f"کد شما با **{model_name}** برای زبان **{lang}** آماده است.",
                            reply_to=event.message.id,
                            buttons=[[back_to_lang_button, new_code_button]] # Add buttons here too
                        )
                        await processing_msg.delete()
                    finally:
                        if os.path.exists(filename):
                            os.remove(filename)
                else:
                    if not response.strip():
                        response_text = "**پاسخی دریافت نشد. لطفا دوباره امتحان کنید یا سوال خود را تغییر دهید.**"
                        buttons_to_show = [[back_to_lang_button]] # Only show back button if no code
                    else:
                        response_text = f"**پاسخ با {model_name} برای زبان {lang}:**\n```{lang.lower()}\n{response}\n```"
                        buttons_to_show = [[back_to_lang_button, new_code_button]] # Show both buttons

                    await processing_msg.edit(
                        response_text,
                        buttons=buttons_to_show,
                        parse_mode='markdown'
                    )
            except Exception as e:
                await processing_msg.edit(f"خطا در نمایش پاسخ: {e}")
                print(f"Error formatting/sending response for user {user_id}: {e}")

        # Clear state *after* processing and sending response
        # State will be re-added if user clicks "New Code" button
        if user_id in user_states:
             del user_states[user_id]

# --- <<< NEW Callback Handler for "New Code" button >>> ---
@client.on(events.CallbackQuery(pattern=b'newcode_(.*)_(.*)'))
async def handle_new_code_request(event):
    """Handles the 'New Code from Current Language' button press."""
    if not bot_active and event.sender_id != admin_id:
        await event.answer("ربات در حال حاضر غیرفعال است.", alert=True)
        return

    user_id = event.sender_id
    try:
        # Extract model and language from callback data
        model_key = event.pattern_match.group(1).decode('utf-8')
        lang = event.pattern_match.group(2).decode('utf-8')

        # Validate extracted data
        if model_key not in AI_MODELS or lang not in languages:
            await event.answer("خطا: اطلاعات دکمه نامعتبر است.", alert=True)
            return

        # Re-establish user state
        user_states[user_id] = {"model": model_key, "language": lang}
        model_name = AI_MODELS.get(model_key, "AI")

        # Edit the message to prompt for a new question
        await event.edit(
            f"**مدل: {model_name}**\n"
            f"**زبان: {lang}**\n\n"
            "✅ بسیار خب! **سوال جدیدت رو برای همین زبان بپرس.**",
            buttons=[
                 Button.inline("🔙 برگشت به انتخاب زبان", f"model_{model_key}".encode('utf-8'))
                 ]
        )
        await event.answer(f"آماده دریافت سوال جدید برای زبان {lang}...") # Subtle confirmation

    except Exception as e:
        print(f"Error handling new code request button: {e}")
        await event.answer("خطایی در پردازش درخواست رخ داد.", alert=True)


# --- Admin Commands ---
# ... (admin_panel, list_started_users_cmd, show_stats, turn_on, turn_off, show_help, broadcast functions remain the same) ...
@client.on(events.NewMessage(pattern='/admin', from_users=admin_id))
async def admin_panel(event):
    msg = """
**⚙️ پنل مدیریت ⚙️**

/on - روشن کردن ربات
/off - خاموش کردن ربات
/broadcast [پیام] - ارسال پیام همگانی (از دیتابیس SQLite)
/list_started - نمایش لیست کاربران استارت کرده (از فایل JSON)
/stats - نمایش تعداد کاربران
    """
    await event.respond(msg)

@client.on(events.NewMessage(pattern="/list_started", from_users=admin_id))
async def list_started_users_cmd(event):
    users = get_started_users_list()
    if not users:
        await event.respond("**هیچ کاربری در لیست فایل JSON یافت نشد.**")
        return

    user_list_md = "**لیست کاربرانی که ربات را استارت کرده‌اند (از JSON):**\n\n"
    count = 0
    errors = 0
    async with client.action(event.chat_id, 'typing'):
        for user_id in users:
            try:
                user = await client.get_entity(user_id)
                username = f"@{user.username}" if user.username else f"ID: `{user.id}`"
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                name = f"{first_name} {last_name}".strip()
                user_list_md += f"- {username} ({name})\n"
                count += 1
            except Exception as e:
                user_list_md += f"- ID: `{user_id}` (خطا در دریافت اطلاعات: {e})\n"
                errors +=1
            await asyncio.sleep(0.1) # Avoid hitting limits

    user_list_md += f"\n**تعداد کل: {count} (خطا: {errors})**"

    if len(user_list_md) > 4096:
        await event.respond("**لیست کاربران طولانی است. ارسال در چند بخش...**")
        parts = [user_list_md[i:i+4000] for i in range(0, len(user_list_md), 4000)]
        for part in parts:
            await client.send_message(admin_id, part, parse_mode='markdown')
    else:
        await event.respond(user_list_md, parse_mode='markdown')


@client.on(events.NewMessage(pattern='/stats', from_users=admin_id))
async def show_stats(event):
    db_count = 0
    try:
        async with aiosqlite.connect("users.db", timeout=5) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                db_count = result[0] if result else 0
    except Exception as e:
        print(f"Error counting DB users: {e}")
        await event.respond(f"خطا در شمارش کاربران دیتابیس: {e}")
        return

    json_count = len(get_started_users_list())

    await event.respond(
        f"📊 **آمار ربات** 📊\n\n"
        f"👤 تعداد کاربران در دیتابیس (SQLite): **{db_count}**\n"
        f"🏁 تعداد کاربران استارت کرده (JSON): **{json_count}**"
    )


@client.on(events.NewMessage(pattern='/on', from_users=admin_id))
async def turn_on(event):
    global bot_active
    bot_active = True
    await event.respond("✅ ربات **روشن** شد.")

@client.on(events.NewMessage(pattern='/off', from_users=admin_id))
async def turn_off(event):
    global bot_active
    bot_active = False
    await event.respond("❌ ربات **خاموش** شد.")


@client.on(events.CallbackQuery(data=b"help"))
async def show_help(event):
    await event.answer()
    help_message = """
    **🌟 راهنمای استفاده از ربات 🌟**

    1️⃣ **انتخاب مدل**: روی "کد نویسی" بزنید و مدل (GPT یا Gemini) را انتخاب کنید.
    2️⃣ **انتخاب زبان**: زبان برنامه‌نویسی را انتخاب کنید.
    3️⃣ **ارسال سوال**: درخواست کدنویسی خود را بنویسید (ربات چک می‌کند مرتبط باشد).
    4️⃣ **دریافت کد**: ربات کد درخواستی را با مدل انتخابی تولید می‌کند.
    5️⃣ **ادامه**: می‌توانید با دکمه "کد جدید از همین زبان" سوال دیگری بپرسید یا با "بازگشت به زبان‌ها" زبان را عوض کنید.

    ⬅️ **بازگشت**: از دکمه‌های "برگشت" استفاده کنید.
    ❗️ **توجه**: فقط درخواست‌های مربوط به برنامه‌نویسی پذیرفته می‌شوند.
    """
    await event.edit(
        help_message,
        buttons=[
            [Button.inline("🏁 شروع کنید!", b"select_ai")],
            [Button.inline("🔙 برگشت به منوی اصلی", b"main_menu")]
        ]
    )


@client.on(events.NewMessage(pattern='/broadcast (.+)', from_users=admin_id))
async def broadcast(event):
    text = event.pattern_match.group(1)
    count = 0
    errors = 0
    await event.respond(f"⏳ در حال شروع ارسال پیام همگانی برای کاربران دیتابیس...")
    try:
        async with aiosqlite.connect("users.db", timeout=10) as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()

        total_users = len(rows)
        if total_users == 0:
             await event.respond("هیچ کاربری در دیتابیس برای ارسال پیام یافت نشد.")
             return

        status_message = await event.respond(f"ارسال به 0 از {total_users} کاربر...")
        for i, row in enumerate(rows):
            user_id = row[0]
            try:
                await client.send_message(user_id, text)
                count += 1
            except Exception as e:
                print(f"Failed to send broadcast to {user_id}: {e}")
                errors += 1
            if (i + 1) % 25 == 0 or (i + 1) == total_users:
                await status_message.edit(f"ارسال به {i+1} از {total_users} کاربر... (موفق: {count}, خطا: {errors})")
                await asyncio.sleep(1)
        await status_message.edit(f"✅ پیام همگانی برای **{count}** کاربر ارسال شد. **{errors}** خطا رخ داد.")
    except aiosqlite.Error as e:
        await event.respond(f"خطا در دسترسی به دیتابیس: {e}")
    except Exception as e:
         await event.respond(f"خطای ناشناخته در ارسال همگانی: {e}")


# --- API Call Functions ---
# ... (call_gpt_api and call_gemini_api remain the same as the previous version with JSON parsing) ...
async def call_gpt_api(query, user_id):
    headers = {
        "authority": "api.binjie.fun", "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br", "accept-language": "en-US,en;q=0.9",
        "origin": "https://chat18.aichatos.xyz", "referer": "https://chat18.aichatos.xyz/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": query, "userId": f"telethon-{user_id}",
        "network": True, "system": "", "withoutContext": True,
        "stream": False
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as http_client:
            res = await http_client.post(GPT_API_URL, headers=headers, json=data)
            res.raise_for_status()
            return res.text.strip()
    except httpx.HTTPStatusError as e:
         print(f"GPT API HTTP Error: {e.response.status_code} - {e.response.text}")
         error_text = e.response.text[:100]
         return f"خطا در ارتباط با سرویس GPT (HTTP {e.response.status_code}).\n`{error_text}...`"
    except httpx.RequestError as e:
        print(f"GPT API Request Error: {e}")
        return f"خطا در شبکه هنگام تماس با سرویس GPT."
    except Exception as e:
        print(f"GPT API Generic Error: {e}")
        return f"خطای ناشناخته در سرویس GPT."

async def call_gemini_api(query, user_id):
    payload = { "prompt": query, "model": GEMINI_MODEL_ID }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(GEMINI_API_URL, json=payload)
            response.raise_for_status()
            try:
                data = response.json()
                result = data.get("result")
                if result is not None and isinstance(result, str):
                    return result.strip()
                else:
                    print(f"Gemini API unexpected JSON structure: {data}")
                    return "خطا: ساختار پاسخ دریافت شده از Gemini نامعتبر است."
            except json.JSONDecodeError:
                print(f"Gemini API non-JSON response: {response.text}")
                return f"خطا: پاسخ غیر JSON از Gemini دریافت شد:\n`{response.text[:100]}...`"
    except httpx.HTTPStatusError as e:
         print(f"Gemini API HTTP Error: {e.response.status_code} - {e.response.text}")
         error_text = e.response.text[:100]
         return f"خطا در ارتباط با سرویس Gemini (HTTP {e.response.status_code}).\n`{error_text}...`"
    except httpx.RequestError as e:
        print(f"Gemini API Request Error: {e}")
        return f"خطا در شبکه هنگام تماس با سرویس Gemini."
    except Exception as e:
        print(f"Gemini API Generic Error: {e}")
        return f"خطای ناشناخته در سرویس Gemini."

# --- Main Execution ---
# ... (main function with BOT_TOKEN handling remains the same) ...
async def main():
    await init_db()
    try:
         BOT_TOKEN = os.environ.get("BOT_TOKEN")
         if not BOT_TOKEN:
              # Fallback: try reading from a file named .env
              try:
                  with open('.env', 'r') as f:
                      for line in f:
                          if line.startswith('BOT_TOKEN='):
                              BOT_TOKEN = line.strip().split('=', 1)[1]
                              break
              except FileNotFoundError:
                  pass # .env file doesn't exist, proceed to raise error or user login

         if not BOT_TOKEN:
              raise ValueError("BOT_TOKEN not found in environment variables or .env file.")

         print("Logging in using Bot Token...")
         await client.start(bot_token=BOT_TOKEN)

    except ValueError as e:
         print(f"Info: {e}")
         print("Attempting user login instead (will ask for phone/code if needed)...")
         await client.start() # Fallback to user login
    except Exception as e:
         print(f"An unexpected error occurred during login: {e}")
         return

    print("ربات با قابلیت انتخاب مدل روشن شد...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Ensure libraries are installed: pip install httpx aiosqlite telethon python-dotenv
    # For Bot login, set environment variable BOT_TOKEN='YOUR_TOKEN_HERE'
    # Or create a file named .env in the same directory with the line: BOT_TOKEN=YOUR_TOKEN_HERE
    # Consider adding python-dotenv: pip install python-dotenv (optional, helps with .env file)
    asyncio.run(main())
