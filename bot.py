# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
import aiosqlite
import json
import httpx # <--- Import httpx
import asyncio
import os

# --- Configuration ---
api_id = 18377832  # Your api_id
api_hash = "ed8556c450c6d0fd68912423325dd09c"  # Your api_hash
session_name = "my_ai_multi_model" # Changed session name slightly
admin_id = 7094106651 # Your Admin ID
json_file = 'users_started.json' # Renamed for clarity

# --- Bot State ---
client = TelegramClient(session_name, api_id, api_hash)
bot_active = True
user_states = {} # Stores {"user_id": {"model": "...", "language": "..."}}

# --- Constants ---
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
    "gpt": "GPT (4)", # Identifier and display name
    "gemini": "Gemini 2.0 Flash"
}

GPT_API_URL = "https://api.binjie.fun/api/generateStream"
GEMINI_API_URL = "https://gem-ehsan.vercel.app/gemini/chat"
GEMINI_MODEL_ID = "2" # As per your requirement

# --- JSON User Tracking (for /list_started) ---
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

# --- SQLite User Tracking (for /broadcast and general user addition) ---
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

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not bot_active and event.sender_id != admin_id:
        return

    user_id = event.sender_id
    await add_user_to_db(user_id) # Add to SQLite DB
    add_started_user(user_id) # Add to JSON list
    user_states.pop(user_id, None) # Clear any previous state

    await event.respond(
        "**سلام، چطوری میتونم کمکت کنم؟**",
        buttons=[
            [Button.inline("🧬 کد نویسی", b"select_ai")], # Changed callback data
            [Button.inline("📚 راهنما", b"help")],
            [Button.url("🧑‍💻 ارتباط با توسعه دهنده", "https://t.me/n6xel")]
        ]
    )

@client.on(events.CallbackQuery(data=b"main_menu"))
async def return_to_main_menu(event):
    user_id = event.sender_id
    user_states.pop(user_id, None) # Clear state when returning to main menu
    await event.edit(
        "**سلام، چطوری میتونم کمکت کنم؟**",
        buttons=[
            [Button.inline("🧬 کد نویسی", b"select_ai")], # Changed callback data
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
    user_states.pop(user_id, None) # Clear previous state if any

    ai_buttons = [
        Button.inline(name, f"model_{key}".encode('utf-8'))
        for key, name in AI_MODELS.items()
    ]

    # Arrange buttons in rows of 2
    rows = []
    for i in range(0, len(ai_buttons), 2):
        rows.append(ai_buttons[i:i+2])

    rows.append([Button.inline("🔙 برگشت به منوی اصلی", b"main_menu")])

    await event.edit(
        "**لطفا مدل هوش مصنوعی را انتخاب کنید:**",
        buttons=rows
    )

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

    # Initialize state for the user with the selected model
    user_states[user_id] = {"model": model_key}

    # --- Now show language selection ---
    lang_buttons = []
    for lang in languages:
        lang_buttons.append(Button.inline(lang, f"lang_{lang}".encode('utf-8'))) # Prefix callback data

    # Arrange buttons in rows of 2
    rows = []
    for i in range(0, len(lang_buttons), 2):
        rows.append(lang_buttons[i:i+2])

    # Add back button to AI selection
    rows.append([Button.inline("🔙 برگشت به انتخاب مدل", b"select_ai")])

    await event.edit(
        f"**مدل انتخاب شده: {AI_MODELS[model_key]}**\n\n"
        "**لطفاً زبان برنامه‌نویسی را انتخاب کنید:**",
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

    # Check if model was already selected (should be)
    if user_id not in user_states or "model" not in user_states[user_id]:
        await event.edit("**خطا: ابتدا باید مدل هوش مصنوعی را انتخاب کنید.**", buttons=[Button.inline("انتخاب مدل", b"select_ai")])
        return

    # Store selected language in user state
    user_states[user_id]["language"] = lang
    selected_model_key = user_states[user_id]["model"]
    selected_model_name = AI_MODELS.get(selected_model_key, "ناشناخته")

    await event.edit(
        f"**مدل: {selected_model_name}**\n"
        f"**زبان: {lang}**\n\n"
        "**سوالت رو بپرس تا کدشو بنویسم.**",
        buttons=[
            Button.inline("🔙 برگشت به انتخاب زبان", f"model_{selected_model_key}".encode('utf-8')) # Back to language list for this model
        ]
    )


@client.on(events.NewMessage)
async def handle_message(event):
    # Ignore commands and non-private messages for this handler
    if event.text.startswith('/') or not event.is_private:
        # Keep this check, but allow admin commands through other handlers
        # Check if it's an admin command and handle appropriately if needed, or let other handlers manage it
        if event.sender_id == admin_id and event.text.startswith('/'):
             return # Let admin command handlers process
        # For non-admin users, ignore commands here
        elif not event.text.startswith('/'):
            pass # Continue processing potential coding requests
        else:
             return # Ignore commands from non-admins


    if not bot_active and event.sender_id != admin_id:
        # Maybe send a message? Or just silently ignore.
        # await event.respond("ربات در حال حاضر غیرفعال است.")
        return

    user_id = event.sender_id
    chat_id = event.chat_id
    user_input = event.text.strip()

    # Check if user is in the process of asking for code
    if user_id in user_states and "model" in user_states[user_id] and "language" in user_states[user_id]:
        lang = user_states[user_id]["language"]
        model = user_states[user_id]["model"]
        model_name = AI_MODELS.get(model, "AI") # Get display name

        # Adjusted prompt for potentially better results, especially for code generation
        prompt = f"Please provide only the {lang} code for the following request, without any explanation before or after the code block:\n\n{user_input}"

        processing_msg = await event.respond(f"**در حال پردازش درخواست شما با {model_name} برای زبان {lang}... لطفاً صبر کنید.**")

        response = None
        async with client.action(chat_id, "typing"):
            try:
                if model == "gemini":
                    response = await call_gemini_api(prompt, user_id)
                elif model == "gpt":
                    # Using a slightly different prompt structure might be better for GPT
                    gpt_prompt = f"{lang}: {user_input}. Only provide the code block as output."
                    response = await call_gpt_api(gpt_prompt, user_id)
                else:
                    response = "خطا: مدل هوش مصنوعی انتخاب شده معتبر نیست."

            except Exception as e:
                response = f"متاسفانه در تولید کد خطایی رخ داد: {e}"
                print(f"Error during API call for user {user_id}: {e}") # Log the error

        # --- Handle Response ---
        if response:
            # Clean up potential markdown backticks if the API includes them
            response = response.strip().strip('`')
            if response.startswith(lang.lower()): # Remove potential language prefix like "python\n"
                 response = response[len(lang):].strip()

            try:
                if len(response) > 4000: # Telegram message limit is ~4096
                    ext = ext_map.get(lang, "txt")
                    filename = f"code_{user_id}_{lang.lower()}.{ext}"
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(response)
                        await client.send_file(
                            event.chat_id,
                            filename,
                            caption=f"کد شما با **{model_name}** برای زبان **{lang}** آماده است.",
                            reply_to=event.message.id # Reply to the user's request message
                        )
                        await processing_msg.delete() # Delete the "processing" message
                    finally:
                        if os.path.exists(filename):
                            os.remove(filename) # Clean up the file
                else:
                    # Ensure response is not empty
                    if not response.strip():
                        response = "**پاسخی دریافت نشد. لطفا دوباره امتحان کنید یا سوال خود را تغییر دهید.**"
                        final_message = response # No code block if empty
                    else:
                        # Format as code block
                        final_message = f"**پاسخ با {model_name} برای زبان {lang}:**\n```{lang.lower()}\n{response}\n```"


                    await processing_msg.edit(
                        final_message,
                        buttons=[
                             Button.inline("🔙 برگشت به انتخاب زبان", f"model_{model}".encode('utf-8')) # Back to language list
                        ],
                         parse_mode='markdown' # Use markdown for code blocks
                    )
            except Exception as e:
                await processing_msg.edit(f"خطا در نمایش پاسخ: {e}")
                print(f"Error formatting/sending response for user {user_id}: {e}")

        # Clear state after processing the request
        if user_id in user_states:
             del user_states[user_id]

# --- Admin Commands ---

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

    # Send in chunks if too long
    if len(user_list_md) > 4096:
        await event.respond("**لیست کاربران طولانی است. ارسال در چند بخش...**")
        parts = [user_list_md[i:i+4000] for i in range(0, len(user_list_md), 4000)]
        for part in parts:
            await client.send_message(admin_id, part, parse_mode='markdown') # Ensure parsing
    else:
        await event.respond(user_list_md, parse_mode='markdown') # Ensure parsing


@client.on(events.NewMessage(pattern='/stats', from_users=admin_id))
async def show_stats(event):
     # Count from SQLite DB
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

    # Count from JSON file
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

    برای استفاده از ربات، مراحل زیر را دنبال کنید:

    1️⃣ **انتخاب مدل**: روی دکمه "کد نویسی" بزنید و مدل هوش مصنوعی (مثل Gemini یا GPT) را انتخاب کنید.
    2️⃣ **انتخاب زبان**: زبان برنامه‌نویسی مورد نظر خود را انتخاب کنید.
    3️⃣ **ارسال سوال**: سوال یا درخواست کدنویسی خود را به زبان انتخابی بنویسید.
    4️⃣ **دریافت کد**: ربات سعی می‌کند بهترین کد ممکن را با استفاده از مدل انتخابی برای شما بنویسد.

    ⬅️ **بازگشت**: از دکمه‌های "برگشت" برای رفتن به مرحله قبل استفاده کنید.

    ❗️ **توجه**: ربات برای پاسخ به درخواست‌های مرتبط با برنامه‌نویسی طراحی شده است.

    💡 از این ربات لذت ببرید!
    """

    await event.edit(
        help_message,
        buttons=[
            [Button.inline("🏁 شروع کنید!", b"select_ai")], # Start with AI selection
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
                rows = await cursor.fetchall() # Fetch all users at once

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
            # Update status periodically to avoid flooding Telegram
            if (i + 1) % 25 == 0 or (i + 1) == total_users: # Update more frequently
                await status_message.edit(f"ارسال به {i+1} از {total_users} کاربر... (موفق: {count}, خطا: {errors})")
                await asyncio.sleep(1) # Small delay

        await status_message.edit(f"✅ پیام همگانی برای **{count}** کاربر ارسال شد. **{errors}** خطا رخ داد.")

    except aiosqlite.Error as e:
        await event.respond(f"خطا در دسترسی به دیتابیس: {e}")
    except Exception as e:
         await event.respond(f"خطای ناشناخته در ارسال همگانی: {e}")

# --- API Call Functions ---

async def call_gpt_api(query, user_id):
    """Calls the Binjie (GPT-like) API."""
    headers = {
        "authority": "api.binjie.fun", "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br", "accept-language": "en-US,en;q=0.9",
        "origin": "https://chat18.aichatos.xyz", "referer": "https://chat18.aichatos.xyz/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36", # Updated UA
        "Content-Type": "application/json"
    }
    data = {
        "prompt": query, "userId": f"telethon-{user_id}", # Make user ID more distinct
        "network": True, "system": "", "withoutContext": True, # Maybe True is better?
        "stream": False
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as http_client: # Increased timeout
            res = await http_client.post(GPT_API_URL, headers=headers, json=data)
            res.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            # Assuming the response is plain text
            return res.text.strip()
    except httpx.HTTPStatusError as e:
         print(f"GPT API HTTP Error: {e.response.status_code} - {e.response.text}")
         # Provide a user-friendly error message
         error_text = e.response.text[:100] # Show only the beginning of the error text
         return f"خطا در ارتباط با سرویس GPT (HTTP {e.response.status_code}).\nپاسخ سرور: `{error_text}...`"
    except httpx.RequestError as e:
        print(f"GPT API Request Error: {e}")
        return f"خطا در شبکه هنگام تماس با سرویس GPT: {e}"
    except Exception as e:
        print(f"GPT API Generic Error: {e}")
        return f"خطای ناشناخته در سرویس GPT: {e}"


async def call_gemini_api(query, user_id):
    """Calls the Vercel Gemini API."""
    payload = {
        "prompt": query,
        "model": GEMINI_MODEL_ID
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client: # Increased timeout
            response = await client.post(GEMINI_API_URL, json=payload)
            response.raise_for_status() # Check for HTTP errors
            # Check content type or just assume text based on user info
            # If it returns JSON like {"response": "...", ...}, adjust accordingly:
            # try:
            #     data = response.json()
            #     return data.get("response", "پاسخ نامعتبر از Gemini دریافت شد.").strip()
            # except json.JSONDecodeError:
            #     return response.text.strip() # Fallback to text
            return response.text.strip() # Assuming plain text response for now
    except httpx.HTTPStatusError as e:
         print(f"Gemini API HTTP Error: {e.response.status_code} - {e.response.text}")
         error_text = e.response.text[:100] # Show only the beginning of the error text
         return f"خطا در ارتباط با سرویس Gemini (HTTP {e.response.status_code}).\nپاسخ سرور: `{error_text}...`"
    except httpx.RequestError as e:
        print(f"Gemini API Request Error: {e}")
        return f"خطا در شبکه هنگام تماس با سرویس Gemini: {e}"
    except Exception as e:
        print(f"Gemini API Generic Error: {e}")
        return f"خطای ناشناخته در سرویس Gemini: {e}"


# --- Main Execution ---
async def main():
    await init_db() # Initialize the database on startup
    await client.start()
    print("ربات با قابلیت انتخاب مدل روشن شد...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Ensure httpx is installed: pip install httpx
    asyncio.run(main())

