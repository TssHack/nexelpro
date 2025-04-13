# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
import aiosqlite
import json
import httpx
import asyncio
import os
from dotenv import load_dotenv # Added for better .env handling

# --- Configuration ---
# Load environment variables from .env file if it exists
load_dotenv()

api_id = os.environ.get("API_ID", 18377832) # Use env var or default
api_hash = os.environ.get("API_HASH", "ed8556c450c6d0fd68912423325dd09c") # Use env var or default
session_name = "my_ai_multi_model"
admin_id = int(os.environ.get("ADMIN_ID", 6856915102)) # Use env var or default, ensure integer
json_file = 'users_started.json'
db_file = 'users.db'

# --- Bot State ---
client = TelegramClient(session_name, api_id, api_hash)
bot_active = True
user_states = {}

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
    "gpt": "GPT-4",
    "gemini": "Gemini 2.0 Flash"
}

GPT_API_URL = "https://api.binjie.fun/api/generateStream"
GEMINI_API_URL = "https://gem-ehsan.vercel.app/gemini/chat"
GEMINI_MODEL_ID = "2" # Should this be a string or integer? API likely expects string.


# --- JSON User Tracking ---
def load_started_users():
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            # Ensure we load a list, even if the file is empty/malformed
            data = json.load(file)
            return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {json_file}. Starting with empty list.")
        return []

def save_started_users(users):
    try:
        with open(json_file, 'w', encoding='utf-8') as file:
            json.dump(users, file, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Error saving started users to {json_file}: {e}")


def add_started_user(user_id):
    users = load_started_users()
    if user_id not in users:
        users.append(user_id)
        save_started_users(users)

def get_started_users_list():
    return load_started_users()


# --- SQLite User Tracking ---
async def init_db():
    try:
        async with aiosqlite.connect(db_file) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
            await db.commit()
    except aiosqlite.Error as e:
        print(f"Database initialization error: {e}")

async def add_user_to_db(user_id):
    try:
        async with aiosqlite.connect(db_file, timeout=10) as db: # Added timeout
            await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            await db.commit()
    except aiosqlite.Error as e:
        print(f"Database error adding user {user_id}: {e}")


# --- Event Handlers ---

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not bot_active and event.sender_id != admin_id:
        # Optionally send a message that the bot is off
        # await event.respond("ربات موقتا غیرفعال است.")
        return
    user_id = event.sender_id
    await add_user_to_db(user_id)
    add_started_user(user_id)
    user_states.pop(user_id, None) # Clear previous state on /start
    await event.respond(
        "**سلام، چطوری میتونم کمکت کنم؟**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
        buttons=[
            [Button.inline("🧬 کد نویسی", b"select_ai")],
            [Button.inline("📚 راهنما", b"help")],
            [Button.url("🧑‍💻 ارتباط با توسعه دهنده", "https://t.me/n6xel")]
        ]
    )

@client.on(events.CallbackQuery(data=b"main_menu"))
async def return_to_main_menu(event):
    user_id = event.sender_id
    user_states.pop(user_id, None) # Clear state when returning to main menu
    try:
        await event.edit(
            "**سلام، چطوری میتونم کمکت کنم؟**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
            buttons=[
                [Button.inline("🧬 کد نویسی", b"select_ai")],
                [Button.inline("📚 راهنما", b"help")],
                [Button.url("🧑‍💻 ارتباط با توسعه دهنده", "https://t.me/n6xel")]
            ]
        )
    except Exception as e:
        print(f"Error editing message for main_menu: {e}")
        # If edit fails, maybe the original message was deleted. Send a new one.
        await event.respond(
             "**سلام، چطوری میتونم کمکت کنم؟**\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
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
    user_states.pop(user_id, None) # Clear any previous state when starting model selection
    ai_buttons = [
        Button.inline(name, f"model_{key}".encode('utf-8'))
        for key, name in AI_MODELS.items()
    ]
    rows = []
    # Arrange buttons in rows of 2
    for i in range(0, len(ai_buttons), 2):
        rows.append(ai_buttons[i:i+2])
    rows.append([Button.inline("🔙 برگشت به منوی اصلی", b"main_menu")])
    try:
        await event.edit("**لطفا مدل هوش مصنوعی را انتخاب کنید:**", buttons=rows)
    except Exception as e:
         print(f"Error editing message for select_ai: {e}")
         await event.answer("خطایی رخ داد، لطفا دوباره امتحان کنید.", alert=True)


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
        await event.answer("خطا در پردازش انتخاب مدل.", alert=True)
        return

    if model_key not in AI_MODELS:
        await event.answer("مدل هوش مصنوعی نامعتبر است.", alert=True)
        return

    # Set the model state for the user
    user_states[user_id] = {"model": model_key}

    lang_buttons = [Button.inline(lang, f"lang_{lang}".encode('utf-8')) for lang in languages]
    rows = []
    # Arrange language buttons in rows of 2
    for i in range(0, len(lang_buttons), 2):
        rows.append(lang_buttons[i:i+2])
    rows.append([Button.inline("🔙 برگشت به انتخاب مدل", b"select_ai")]) # Button to go back to AI model selection

    try:
        await event.edit(
            f"**مدل انتخاب شده: {AI_MODELS[model_key]}**\n\n"
            f"**لطفاً زبان برنامه‌نویسی مورد نظر خود را انتخاب کنید:**",
            buttons=rows
        )
    except Exception as e:
         print(f"Error editing message for model selection ({model_key}): {e}")
         await event.answer("خطایی رخ داد، لطفا دوباره مدل را انتخاب کنید.", alert=True)


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
        await event.answer("زبان برنامه‌نویسی نامعتبر است.", alert=True)
        return

    # Ensure the user has selected a model first
    if user_id not in user_states or "model" not in user_states[user_id]:
        await event.answer("خطا: ابتدا باید مدل هوش مصنوعی را انتخاب کنید.", alert=True)
        # Try to send them back to model selection
        await choose_ai_model(event)
        return

    # Update user state with selected language
    user_states[user_id]["language"] = lang
    selected_model_key = user_states[user_id]["model"]
    selected_model_name = AI_MODELS.get(selected_model_key, "ناشناخته")

    try:
        await event.edit(
            f"**مدل: {selected_model_name}**\n"
            f"**زبان: {lang}**\n\n"
            "✅ بسیار خب! **حالا سوال یا درخواست کدنویسی خود را بنویسید:**",
            buttons=[
                # Button to go back to language selection for the *current* model
                Button.inline("🔙 برگشت به انتخاب زبان", f"model_{selected_model_key}".encode('utf-8'))
            ]
        )
    except Exception as e:
        print(f"Error editing message for language selection ({lang}): {e}")
        await event.answer("خطایی رخ داد، لطفا دوباره زبان را انتخاب کنید.", alert=True)

# --- Helper function to check if input is code-related ---
async def is_code_related(text, user_id):
    """Uses GPT (Binjie) to check if the text is a valid code generation request."""
    # Using a simpler, more reliable model for this check might be better if available.
    # Binjie might be overkill or sometimes unreliable for simple yes/no.
    # Consider adding keywords check as a fallback if API fails.
    check_prompt = f'Is the following message a valid request for generating programming code? Answer only with "yes" or "no".\n\n"{text}"'
    try:
        print(f"Checking relevance for user {user_id}: {text[:50]}...")
        # Use a specific ID for validator calls to avoid mixing contexts if possible
        reply = await call_gpt_api(check_prompt, f"validator-{user_id}")
        print(f"Relevance check reply: {reply}")
        # Make the check more robust (case-insensitive, strips whitespace)
        return "yes" in reply.lower().strip()
    except Exception as e:
        print(f"Error during code relevance check: {e}")
        # Fallback to assuming it IS code-related if the check fails,
        # to avoid blocking users unnecessarily. Or return False to be stricter.
        # Let's be strict for now.
        return False


# --- Main Message Handler ---
@client.on(events.NewMessage)
async def handle_message(event):
    # Ignore non-private messages unless it's an admin command
    if not event.is_private and event.sender_id != admin_id:
        return
    # Ignore commands unless it's the admin or it's /start
    if event.text.startswith('/') and event.text != '/start' and event.sender_id != admin_id:
        return
    # Allow admin commands to proceed
    if event.text.startswith('/') and event.sender_id == admin_id:
        # Let admin command handlers take over
        # We return here to prevent this handler from processing admin commands
        # like /on, /off, /stats etc.
        # We already have specific handlers for those.
        # Exception: Let /start be handled by its specific handler above.
        if event.text.startswith('/admin') or \
           event.text.startswith('/list_started') or \
           event.text.startswith('/stats') or \
           event.text.startswith('/on') or \
           event.text.startswith('/off') or \
           event.text.startswith('/broadcast'):
            return # Handled by dedicated admin functions

    # Check if bot is active (for non-admin users)
    if not bot_active and event.sender_id != admin_id:
        # Silently ignore messages or send a message
        # await event.respond("ربات در حال حاضر غیرفعال است.")
        return

    user_id = event.sender_id
    chat_id = event.chat_id
    user_input = event.text.strip()

    # Check if the user is in a state where they should be asking a question
    if user_id in user_states and "model" in user_states[user_id] and "language" in user_states[user_id]:
        lang = user_states[user_id]["language"]
        model = user_states[user_id]["model"]
        model_name = AI_MODELS.get(model, "AI") # Default to "AI" if model key somehow invalid

        # --- Relevance Check ---
        processing_check_msg = await event.respond("🔍 در حال بررسی درخواست شما...")
        async with client.action(chat_id, "typing"):
            try:
                is_valid = await is_code_related(user_input, user_id)
            except Exception as e:
                 print(f"Exception in is_code_related call: {e}")
                 is_valid = False # Treat check error as invalid request
                 await processing_check_msg.edit("⚠️ خطایی در بررسی درخواست رخ داد. لطفا دوباره تلاش کنید.")
                 await asyncio.sleep(3) # Give user time to see the error

        # --- Handle Invalid (Non-Code) Request ---
        # <<< MODIFIED BLOCK START >>>
        if not is_valid:
            # Get the selected model and language for the retry button
            model = user_states[user_id]["model"]
            lang = user_states[user_id]["language"]

            # Define the Retry button using the 'newcode' callback pattern
            retry_button_callback_data = f"newcode_{model}_{lang}".encode('utf-8')
            retry_button = Button.inline("🔄 تلاش مجدد", retry_button_callback_data)

            # Define the Back button to go back to language selection for the current model
            back_button_callback_data = f"model_{model}".encode('utf-8')
            back_button = Button.inline("🔙 انتخاب زبان دیگر", back_button_callback_data)

            try:
                await processing_check_msg.edit( # Edit the "checking" message
                    "**متاسفم، به نظر نمی‌رسه این یک درخواست معتبر برای نوشتن کد باشه.**\n\n"
                    "لطفاً درخواست مربوط به برنامه‌نویسی رو مطرح کن، دوباره تلاش کن یا زبان را عوض کن.",
                    buttons=[[retry_button, back_button]] # Add the Retry and Back buttons
                )
            except Exception as e:
                 print(f"Error editing message for invalid request: {e}")
                 # Fallback if edit fails
                 await event.respond(
                     "**متاسفم، به نظر نمی‌رسه این یک درخواست معتبر برای نوشتن کد باشه.**\n\n"
                     "لطفاً درخواست مربوط به برنامه‌نویسی رو مطرح کن، دوباره تلاش کن یا زبان را عوض کن.",
                     buttons=[[retry_button, back_button]]
                 )

            # Keep the user state so the retry button works.
            return # Stop further processing for this message
        # <<< MODIFIED BLOCK END >>>

        # --- Handle Valid Code Request ---
        prompt = f"Please provide only the {lang} code for the following request, without any explanation before or after the code block:\n\n{user_input}"
        # Adjust prompt specifically for GPT if needed (sometimes direct requests work better)
        if model == "gpt":
             gpt_prompt = f"Generate the {lang} code for this request: '{user_input}'. Provide only the raw code block, without any introductory or concluding text, and without using markdown formatting like ```."
             prompt_to_use = gpt_prompt
        else:
             prompt_to_use = prompt

        # Edit the "checking" message to "processing"
        try:
            processing_msg = await processing_check_msg.edit(f"**⏳ در حال پردازش درخواست شما با {model_name} برای زبان {lang}... لطفاً کمی صبر کنید.**")
        except Exception as e:
            print(f"Error editing 'checking' msg to 'processing': {e}")
            # If edit fails, send a new processing message
            processing_msg = await event.respond(f"**⏳ در حال پردازش درخواست شما با {model_name} برای زبان {lang}... لطفاً کمی صبر کنید.**")


        response = None
        async with client.action(chat_id, "typing"):
            try:
                if model == "gemini":
                    response = await call_gemini_api(prompt_to_use, user_id)
                elif model == "gpt":
                    response = await call_gpt_api(prompt_to_use, user_id)
                else:
                    response = "خطا: مدل هوش مصنوعی انتخاب شده معتبر نیست."
            except Exception as e:
                response = f"متاسفانه در تولید کد خطایی رخ داد: {e}"
                print(f"Error during API call for user {user_id}: {e}")

        # --- Process and Send Response ---
        if response:
            # Basic cleaning of the response
            response = response.strip()
            # Remove potential markdown code blocks ``` ```
            if response.startswith("```") and response.endswith("```"):
                 response = response[3:-3].strip()
            # Remove potential language hint at the start (e.g., "python\n...")
            if response.lower().startswith(lang.lower()):
                 response = response[len(lang):].strip()

            # --- Button Definitions for the result message ---
            back_to_lang_button = Button.inline(
                "🔙 برگشت به زبان‌ها",
                f"model_{model}".encode('utf-8') # Goes back to language selection for the current model
            )
            new_code_button = Button.inline(
                "🔄 کد جدید از همین زبان",
                f"newcode_{model}_{lang}".encode('utf-8') # Triggers handle_new_code_request
            )

            try:
                if len(response) > 4000: # Telegram message length limit
                    ext = ext_map.get(lang, "txt")
                    filename = f"code_{user_id}_{lang.lower()}.{ext}"
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(response)
                        # Send file with buttons
                        await client.send_file(
                            event.chat_id,
                            filename,
                            caption=f"✅ کد شما با **{model_name}** برای زبان **{lang}** آماده است (به صورت فایل به دلیل طولانی بودن).",
                            reply_to=event.message.id,
                            buttons=[[new_code_button], [back_to_lang_button]] # Arrange buttons vertically
                        )
                        # Delete the "processing" message after sending the file
                        await processing_msg.delete()
                    except IOError as e:
                        print(f"Error writing code file: {e}")
                        await processing_msg.edit(f"خطا در ذخیره فایل کد: {e}")
                    finally:
                        # Ensure file is deleted after sending
                        if os.path.exists(filename):
                            try:
                                os.remove(filename)
                            except OSError as e:
                                print(f"Error removing temp code file {filename}: {e}")
                else:
                    # Check if the response is empty after cleaning
                    if not response.strip():
                        response_text = "**پاسخی دریافت نشد یا پاسخ خالی بود.**\n\nلطفا دوباره امتحان کنید یا سوال خود را واضح‌تر بیان کنید."
                        buttons_to_show = [[new_code_button], [back_to_lang_button]] # Allow retry or back
                    else:
                        # Format response in a code block
                        # Use lang.lower() for markdown hint, fallback to blank if lang unknown
                        lang_hint = lang.lower() if lang in ext_map else ""
                        response_text = f"✅ **پاسخ با {model_name} برای زبان {lang}:**\n```{lang_hint}\n{response}\n```"
                        buttons_to_show = [[new_code_button], [back_to_lang_button]] # Show both buttons

                    # Edit the "processing" message with the final result
                    await processing_msg.edit(
                        response_text,
                        buttons=buttons_to_show,
                        parse_mode='markdown',
                        link_preview=False # Often not needed for code
                    )
            except Exception as e:
                # Catch potential errors during message editing/sending
                error_message = f"خطا در نمایش پاسخ: {e}\n\nممکن است پاسخ دریافتی قابل نمایش نباشد."
                print(f"Error formatting/sending response for user {user_id}: {e}")
                try:
                    await processing_msg.edit(error_message)
                except Exception as edit_err:
                    print(f"Failed to even edit the error message: {edit_err}")
                    # Final fallback: send a new message if edit fails
                    await event.respond(error_message)

        else:
            # Handle cases where the API call itself failed or returned None/empty
             try:
                 await processing_msg.edit(
                     f"**متاسفانه مشکلی در ارتباط با {model_name} پیش آمد.**\n\nلطفا لحظاتی دیگر دوباره امتحان کنید.",
                      buttons=[
                          [Button.inline("🔄 تلاش مجدد", f"newcode_{model}_{lang}".encode('utf-8'))],
                          [Button.inline("🔙 برگشت به زبان‌ها", f"model_{model}".encode('utf-8'))]
                      ]
                 )
             except Exception as e:
                  print(f"Error editing message for API failure: {e}")


        # Clear user state *after* processing and sending the response.
        # The state will be re-added if the user clicks the "New Code" or "Retry" button.
        # This prevents accidental triggering if they just type something random after getting a result.
        if user_id in user_states:
             del user_states[user_id]

    # If the user sends a message but isn't in the 'asking question' state,
    # guide them to start the process or ignore.
    elif not event.text.startswith('/'): # Ignore commands already handled
        # Check if the message could be mistaken for a command by the user
        if event.text.lower() in ["help", "start", "menu"]:
             await start(event) # Treat as /start
        else:
            # Send a gentle reminder to use the buttons if they haven't started the flow
             await event.respond(
                "لطفا از دکمه‌ها برای شروع کار با ربات استفاده کنید.",
                buttons=[
                    [Button.inline("🧬 شروع کد نویسی", b"select_ai")],
                    [Button.inline("📚 راهنما", b"help")]
                ]
             )


# --- Callback Handler for "New Code" / "Retry" button ---
@client.on(events.CallbackQuery(pattern=b'newcode_(.*)_(.*)'))
async def handle_new_code_request(event):
    """Handles the 'New Code from Current Language' or 'Retry' button press."""
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
            # Try to recover by sending to model selection
            await choose_ai_model(event)
            return

        # Re-establish user state
        user_states[user_id] = {"model": model_key, "language": lang}
        model_name = AI_MODELS.get(model_key, "AI") # Default to "AI"

        # Edit the message to prompt for a new question
        await event.edit(
            f"**مدل: {model_name}**\n"
            f"**زبان: {lang}**\n\n"
            "✅ بسیار خب! **سوال جدیدت رو برای همین زبان بپرس.**",
            buttons=[
                 # Button to go back to language selection for the current model
                 Button.inline("🔙 برگشت به انتخاب زبان", f"model_{model_key}".encode('utf-8'))
            ]
        )
        # Give a subtle confirmation via answer()
        await event.answer(f"آماده دریافت سوال جدید برای زبان {lang}...")

    except Exception as e:
        print(f"Error handling new code/retry request button: {e}")
        await event.answer("خطایی در پردازش درخواست رخ داد.", alert=True)


# --- Admin Commands ---
@client.on(events.NewMessage(pattern='/admin', from_users=admin_id))
async def admin_panel(event):
    msg = """
**⚙️ پنل مدیریت ربات ⚙️**

دستورات موجود:
/on - ✅ روشن کردن ربات برای کاربران
/off - ❌ خاموش کردن ربات برای کاربران
/broadcast `[پیام]` - 📢 ارسال پیام همگانی (به کاربران در دیتابیس SQLite)
/list_started - 📄 نمایش لیست کاربران استارت کرده (از فایل JSON)
/stats - 📊 نمایش تعداد کاربران (SQLite و JSON)
/admin - نمایش همین پنل

*توجه: ربات همیشه برای ادمین فعال است.*
    """
    await event.respond(msg, parse_mode='markdown')

@client.on(events.NewMessage(pattern="/list_started", from_users=admin_id))
async def list_started_users_cmd(event):
    await event.respond("⏳ در حال خواندن لیست کاربران از فایل JSON...")
    users = get_started_users_list()
    if not users:
        await event.respond("**هیچ کاربری در لیست فایل JSON یافت نشد.**")
        return

    user_list_md = "**لیست کاربرانی که ربات را استارت کرده‌اند (از JSON):**\n\n"
    count = 0
    errors = 0
    total_users = len(users)
    status_message = await event.respond(f"🔍 در حال دریافت اطلاعات برای 0 از {total_users} کاربر...")

    async with client.action(event.chat_id, 'typing'):
        for i, user_id in enumerate(users):
            try:
                user = await client.get_entity(user_id)
                username = f"@{user.username}" if user.username else f"ID: `{user.id}`"
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                name = f"{first_name} {last_name}".strip()
                user_list_md += f"- {name} ({username})\n"
                count += 1
            except Exception as e:
                user_list_md += f"- ID: `{user_id}` (⚠️ خطا در دریافت اطلاعات: {e})\n"
                errors +=1
                print(f"Error getting entity for {user_id}: {e}")
            # Update status periodically to avoid hitting limits and show progress
            if (i + 1) % 20 == 0 or (i + 1) == total_users:
                 try:
                     await status_message.edit(f"🔍 در حال دریافت اطلاعات برای {i+1} از {total_users} کاربر...")
                 except Exception: # Ignore potential message edit errors if it was deleted
                     pass
                 await asyncio.sleep(0.5) # Small delay

    user_list_md += f"\n**تعداد کل یافت شده: {count} (خطا در دریافت اطلاعات: {errors})**"

    # Delete status message and send the final list
    try:
         await status_message.delete()
    except Exception:
         pass

    # Send the list, potentially in parts
    if len(user_list_md) > 4096:
        await event.respond("**لیست کاربران طولانی است. ارسال در چند بخش...**")
        # Split message carefully, avoiding splitting markdown formatting
        parts = []
        current_part = ""
        for line in user_list_md.splitlines():
            if len(current_part) + len(line) + 1 < 4000: # Leave buffer
                current_part += line + "\n"
            else:
                parts.append(current_part)
                current_part = line + "\n"
        parts.append(current_part) # Add the last part

        for part in parts:
            await client.send_message(admin_id, part, parse_mode='markdown', link_preview=False)
            await asyncio.sleep(1) # Delay between parts
    else:
        await event.respond(user_list_md, parse_mode='markdown', link_preview=False)


@client.on(events.NewMessage(pattern='/stats', from_users=admin_id))
async def show_stats(event):
    db_count = 0
    db_error = None
    try:
        async with aiosqlite.connect(db_file, timeout=10) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                db_count = result[0] if result else 0
    except Exception as e:
        print(f"Error counting DB users: {e}")
        db_error = str(e)

    json_users = get_started_users_list()
    json_count = len(json_users)

    stats_message = f"📊 **آمار ربات** 📊\n\n"
    if db_error:
        stats_message += f"⚠️ خطا در دسترسی به دیتابیس SQLite: `{db_error}`\n"
    else:
        stats_message += f"👤 تعداد کاربران در دیتابیس (SQLite): **{db_count}**\n"

    stats_message += f"🏁 تعداد کاربران استارت کرده (JSON): **{json_count}**\n\n"
    stats_message += f"وضعیت ربات: **{'✅ فعال' if bot_active else '❌ غیرفعال'}**"


    await event.respond(stats_message)


@client.on(events.NewMessage(pattern='/on', from_users=admin_id))
async def turn_on(event):
    global bot_active
    if bot_active:
         await event.respond("✅ ربات از قبل روشن بود.")
    else:
         bot_active = True
         await event.respond("✅ ربات برای کاربران **روشن** شد.")

@client.on(events.NewMessage(pattern='/off', from_users=admin_id))
async def turn_off(event):
    global bot_active
    if not bot_active:
         await event.respond("❌ ربات از قبل خاموش بود.")
    else:
        bot_active = False
        await event.respond("❌ ربات برای کاربران **خاموش** شد.")


@client.on(events.CallbackQuery(data=b"help"))
async def show_help(event):
    await event.answer() # Acknowledge the button press
    help_message = """
    **🌟 راهنمای استفاده از ربات کدنویس 🌟**

    1️⃣ **شروع**: روی دکمه "🧬 کد نویسی" در منوی اصلی کلیک کنید.
    2️⃣ **انتخاب مدل**: یکی از مدل‌های هوش مصنوعی موجود (مانند GPT یا Gemini) را انتخاب کنید.
    3️⃣ **انتخاب زبان**: زبان برنامه‌نویسی مورد نظرتان را از لیست انتخاب کنید.
    4️⃣ **ارسال سوال**: درخواست کدنویسی خود را به صورت متنی بنویسید و ارسال کنید.
       *(ربات ابتدا بررسی می‌کند که آیا درخواست شما مربوط به کدنویسی است یا خیر)*.
    5️⃣ **دریافت کد**: اگر درخواست معتبر باشد، ربات کد درخواستی را با استفاده از مدل و زبان انتخابی شما تولید و ارسال می‌کند.
    6️⃣ **ادامه**:
       - با دکمه "🔄 کد جدید از همین زبان" می‌توانید سوال دیگری برای همان زبان و مدل بپرسید.
       - با دکمه "🔙 برگشت به زبان‌ها" می‌توانید زبان دیگری را برای مدل فعلی انتخاب کنید.
       - با دکمه "🔙 برگشت به انتخاب مدل" یا "🔙 برگشت به منوی اصلی" می‌توانید به مراحل قبل برگردید.

    ⬅️ **بازگشت**: همیشه می‌توانید از دکمه‌های "برگشت" در مراحل مختلف استفاده کنید.
    ❗️ **توجه**: این ربات برای تولید کد طراحی شده است. لطفا فقط درخواست‌های مربوط به برنامه‌نویسی ارسال کنید.
    """
    try:
        await event.edit(
            help_message,
            buttons=[
                [Button.inline("🧬 شروع کد نویسی", b"select_ai")],
                [Button.inline("🔙 برگشت به منوی اصلی", b"main_menu")]
            ]
        )
    except Exception as e:
         print(f"Error editing help message: {e}")
         # Fallback if edit fails
         await event.respond(help_message, buttons=[[Button.inline("🧬 شروع کد نویسی", b"select_ai")],[Button.inline("🔙 برگشت به منوی اصلی", b"main_menu")]])


@client.on(events.NewMessage(pattern='/broadcast (.+)', from_users=admin_id, func=lambda e: e.is_private))
async def broadcast(event):
    text = event.pattern_match.group(1).strip()
    if not text:
        await event.respond("لطفا پیامی که میخواهید ارسال کنید را بعد از دستور بنویسید. مثال: `/broadcast سلام به همه`")
        return

    sent_count = 0
    error_count = 0
    user_ids = []

    # Fetch users from SQLite DB
    await event.respond("⏳ در حال دریافت لیست کاربران از دیتابیس...")
    try:
        async with aiosqlite.connect(db_file, timeout=10) as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()
                user_ids = [row[0] for row in rows]
    except aiosqlite.Error as e:
        await event.respond(f"❌ خطا در دسترسی به دیتابیس: {e}")
        return
    except Exception as e:
        await event.respond(f"❌ خطای ناشناخته در خواندن دیتابیس: {e}")
        return

    total_users = len(user_ids)
    if total_users == 0:
         await event.respond("هیچ کاربری در دیتابیس برای ارسال پیام یافت نشد.")
         return

    status_message = await event.respond(f"⏳ شروع ارسال پیام همگانی به {total_users} کاربر...")
    start_time = asyncio.get_event_loop().time()

    for i, user_id in enumerate(user_ids):
        try:
            # Use send_message for better error handling than respond
            await client.send_message(user_id, text, parse_mode='markdown', link_preview=False)
            sent_count += 1
        except (ValueError, TypeError) as e:
             # Likely invalid user ID or peer, log and count as error
             print(f"Broadcast Error (Invalid Peer) for {user_id}: {e}")
             error_count += 1
        except Exception as e: # Catch specific Telethon errors if needed
            # Handle potential blocks, deactivations, etc.
            print(f"Failed to send broadcast to {user_id}: {e}")
            error_count += 1

        # Update status periodically and add delays to avoid flood limits
        if (i + 1) % 30 == 0 or (i + 1) == total_users: # Update every 30 users or at the end
            elapsed_time = asyncio.get_event_loop().time() - start_time
            try:
                await status_message.edit(
                    f"📨 ارسال به {i+1} از {total_users} کاربر...\n"
                    f"✅ موفق: {sent_count}\n"
                    f"❌ خطا: {error_count}\n"
                    f"⏱️ زمان سپری شده: {elapsed_time:.2f} ثانیه"
                )
            except Exception: # Ignore edit errors (e.g., message too old)
                pass
            await asyncio.sleep(1.5) # Increase delay between batches slightly

    # Final status update
    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time
    final_message = (
        f"🏁 **ارسال پیام همگانی به پایان رسید.**\n\n"
        f"👥 کل کاربران هدف: {total_users}\n"
        f"✅ پیام با موفقیت برای **{sent_count}** کاربر ارسال شد.\n"
        f"❌ **{error_count}** خطا در ارسال رخ داد (کاربران غیرفعال، ربات بلاک شده و غیره).\n"
        f"⏱️ کل زمان ارسال: {total_time:.2f} ثانیه."
    )
    try:
        await status_message.edit(final_message)
    except Exception:
        await event.respond(final_message) # Send final status if edit fails


# --- API Call Functions ---
async def call_gpt_api(query, user_id):
    headers = {
        "authority": "api.binjie.fun",
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "[https://chat18.aichatos.xyz](https://chat18.aichatos.xyz)", # Ensure this origin is still valid
        "referer": "[https://chat18.aichatos.xyz/](https://chat18.aichatos.xyz/)", # Ensure this referer is still valid
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36", # Keep User-Agent updated
    }
    # Data payload might need adjustments based on API changes
    data = {
        "prompt": query,
        "userId": f"#/{session_name}/{user_id}", # Using a more structured ID
        "network": True, # Keep True if needed
        "system": "", # Add system prompt if desired
        "withoutContext": True, # Keep True for single-turn requests
        "stream": False # We need the full response, not stream
    }
    api_timeout = httpx.Timeout(45.0, connect=10.0) # 45s total, 10s connect

    try:
        async with httpx.AsyncClient(timeout=api_timeout, follow_redirects=True) as http_client:
            print(f"GPT Request to {GPT_API_URL} for {user_id}: {query[:60]}...")
            res = await http_client.post(GPT_API_URL, headers=headers, json=data)
            # Check for non-200 status codes
            res.raise_for_status()
            # Attempt to return the raw text, assuming it's the direct response
            # This API might have changed, might return JSON, needs testing
            response_text = res.text.strip()
            print(f"GPT Raw Response for {user_id}: {response_text[:100]}...") # Log beginning of response
            return response_text
    except httpx.HTTPStatusError as e:
         # Log detailed HTTP error
         error_body = e.response.text[:200] # Limit error body length
         print(f"GPT API HTTP Error for {user_id}: {e.response.status_code} - {error_body}")
         return f"خطا در ارتباط با سرویس GPT (کد: {e.response.status_code}). ممکن است سرویس موقتا در دسترس نباشد.\n`{error_body}...`"
    except httpx.RequestError as e:
        # Log network or request related errors
        print(f"GPT API Request Error for {user_id}: {e}")
        return f"خطا در شبکه هنگام تماس با سرویس GPT. لطفا اتصال اینترنت خود را بررسی کنید."
    except Exception as e:
        # Log any other unexpected errors during the API call
        print(f"GPT API Generic Error for {user_id}: {type(e).__name__} - {e}")
        return f"خطای ناشناخته‌ای در سرویس GPT رخ داد."

async def call_gemini_api(query, user_id):
    # Ensure GEMINI_MODEL_ID is a string if the API expects it
    payload = { "prompt": query, "model": str(GEMINI_MODEL_ID) }
    api_timeout = httpx.Timeout(45.0, connect=10.0) # Consistent timeout

    try:
        async with httpx.AsyncClient(timeout=api_timeout, follow_redirects=True) as client:
            print(f"Gemini Request to {GEMINI_API_URL} for {user_id}: {query[:60]}...")
            response = await client.post(GEMINI_API_URL, json=payload)
            response.raise_for_status() # Check for HTTP errors

            # Try parsing JSON, handle potential errors
            try:
                data = response.json()
                print(f"Gemini Raw JSON Response for {user_id}: {str(data)[:200]}...") # Log beginning of JSON response
                result = data.get("result") # Look for the 'result' key

                # Check if 'result' exists and is a non-empty string
                if result is not None and isinstance(result, str) and result.strip():
                    return result.strip()
                else:
                    # Log unexpected structure or empty result
                    print(f"Gemini API unexpected structure or empty result for {user_id}: {data}")
                    # Provide a more informative error based on what was received
                    if result == "":
                        return "خطا: سرویس Gemini پاسخی ارسال نکرد (پاسخ خالی)."
                    else:
                        return f"خطا: ساختار پاسخ دریافت شده از Gemini نامعتبر است. کلید 'result' یافت نشد یا معتبر نیست."

            except json.JSONDecodeError:
                # Log if the response wasn't valid JSON
                response_text = response.text[:200] # Limit text length
                print(f"Gemini API non-JSON response for {user_id}: {response_text}")
                return f"خطا: پاسخ غیر JSON از Gemini دریافت شد.\n`{response_text}...`"

    except httpx.HTTPStatusError as e:
         error_body = e.response.text[:200]
         print(f"Gemini API HTTP Error for {user_id}: {e.response.status_code} - {error_body}")
         return f"خطا در ارتباط با سرویس Gemini (کد: {e.response.status_code}).\n`{error_body}...`"
    except httpx.RequestError as e:
        print(f"Gemini API Request Error for {user_id}: {e}")
        return f"خطا در شبکه هنگام تماس با سرویس Gemini."
    except Exception as e:
        print(f"Gemini API Generic Error for {user_id}: {type(e).__name__} - {e}")
        return f"خطای ناشناخته در سرویس Gemini."

# --- Main Execution ---
async def main():
    print("Initializing database...")
    await init_db()
    print("Database initialized.")

    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    if not BOT_TOKEN:
         print("Warning: BOT_TOKEN not found in environment variables.")
         # Attempting user login if token is missing
         print("Attempting interactive user login...")
         try:
             await client.start()
         except Exception as e:
              print(f"Fatal Error: Could not log in interactively: {e}")
              return # Exit if login fails completely
    else:
        print("Logging in using Bot Token...")
        try:
            # Ensure API ID and Hash are integers/strings as required by Telethon
            await client.start(bot_token=BOT_TOKEN)
        except Exception as e:
             print(f"Fatal Error: Could not log in using Bot Token: {e}")
             print("Please ensure the BOT_TOKEN is correct and the bot is added to BotFather.")
             # Optionally, try interactive login as fallback?
             # print("Attempting interactive user login as fallback...")
             # try:
             #     await client.start()
             # except Exception as ie:
             #      print(f"Interactive login failed as well: {ie}")
             #      return
             return # Exit if bot token login fails

    # Get bot info after successful login
    try:
        me = await client.get_me()
        print(f"Successfully logged in as: {me.first_name} (@{me.username}) - ID: {me.id}")
        print(f"Admin ID set to: {admin_id}")
        print(f"Bot active status: {bot_active}")
        print("Bot is running...")
    except Exception as e:
         print(f"Could not get bot info after login: {e}")
         print("Bot is running but self-identification failed.")


    # Keep the bot running until disconnected
    await client.run_until_disconnected()

if __name__ == '__main__':
    print("Starting bot script...")
    # --- Instructions ---
    # 1. Make sure libraries are installed:
    #    pip install telethon httpx aiosqlite python-dotenv
    # 2. Create a file named '.env' in the same directory.
    # 3. Add your credentials to the '.env' file:
    #    API_ID=1234567
    #    API_HASH=your_api_hash_here
    #    ADMIN_ID=your_telegram_user_id
    #    BOT_TOKEN=your_bot_token_from_botfather
    # 4. Run the script: python your_script_name.py
    # --- End Instructions ---
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped manually.")
    except Exception as e:
         print(f"\nAn unexpected error occurred in the main loop: {e}")
