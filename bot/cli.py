#!/usr/bin/env python3
"""
ZeroSess CLI - Terminal & Termux Session String Generator
Interactive CLI to generate Pyrogram v2 & Telethon session strings securely in terminal.
"""

import sys
import asyncio
import getpass
from pyrogram import Client
from pyrogram.errors import (
    ApiIdInvalid, PhoneNumberInvalid, PhoneNumberBanned, PhoneNumberFlood,
    PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded,
    PasswordHashInvalid, FloodWait, AccessTokenInvalid
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    ApiIdInvalidError, PhoneNumberInvalidError, PhoneNumberBannedError,
    PhoneNumberFloodError, PhoneCodeInvalidError, PhoneCodeExpiredError,
    SessionPasswordNeededError, PasswordHashInvalidError, FloodWaitError
)

BANNER = r"""
  ______               _____               
 |___  /              / ____|              
    / / ___ _ __ ___ | (___   ___  ___ ___ 
   / / / _ \ '__/ _ \ \___ \ / _ \/ __/ __|
  / /_|  __/ | | (_) |____) |  __/\__ \__ \
 /_____\___|_|  \___/|_____/ \___||___/___/
 ⚡ High-Speed Telegram String Session Generator
"""

def print_banner():
    print("\033[1;36m" + BANNER + "\033[0m")
    print("\033[1;32m[+] Safe & Secure • Zero-PII • In-Memory Execution\033[0m\n")

async def generate_pyrogram_cli():
    print("\n\033[1;33m--- Pyrogram v2 Session Generation ---\033[0m")
    api_id_raw = input("Enter API_ID (from my.telegram.org): ").strip()
    if not api_id_raw.isdigit():
        print("\033[1;31m[!] Invalid API_ID. Must be numbers.\033[0m")
        return
    api_id = int(api_id_raw)
    api_hash = input("Enter API_HASH: ").strip()

    mode = input("Select Type [1] User Account  [2] Bot Token MTProto: ").strip()
    
    if mode == "2":
        bot_token = input("Enter BOT_TOKEN (from @BotFather): ").strip()
        client = Client(name="cli_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token, in_memory=True)
        try:
            await client.start()
            session = await client.export_session_string()
            me = await client.get_me()
            print("\n\033[1;32m[✓] Bot Session String Generated Successfully!\033[0m")
            print(f"Bot: @{me.username} ({me.id})\n")
            print(f"\033[1;37m{session}\033[0m\n")
        except AccessTokenInvalid:
            print("\033[1;31m[!] Invalid Bot Token.\033[0m")
        except Exception as e:
            print(f"\033[1;31m[!] Error: {e}\033[0m")
        finally:
            if client.is_connected:
                await client.stop()
        return

    phone = input("Enter Phone Number (with country code, e.g. +1234567890): ").strip()
    client = Client(name="cli_user", api_id=api_id, api_hash=api_hash, in_memory=True)
    
    try:
        await client.connect()
        sent_code = await client.send_code(phone)
        otp = input("Enter OTP Code sent to Telegram: ").strip().replace(" ", "").replace("-", "")
        
        try:
            await client.sign_in(phone, sent_code.phone_code_hash, otp)
        except SessionPasswordNeeded:
            password = getpass.getpass("Enter 2FA Password: ").strip()
            await client.check_password(password)
            
        session = await client.export_session_string()
        me = await client.get_me()
        print("\n\033[1;32m[✓] Pyrogram v2 Session Generated Successfully!\033[0m")
        print(f"User: {me.first_name} (@{me.username or 'No Username'}) | ID: {me.id}\n")
        print("\033[1;33m--- YOUR SESSION STRING (DO NOT SHARE) ---\033[0m")
        print(f"\033[1;37m{session}\033[0m\n")
    except (PhoneCodeInvalid, PhoneCodeExpired):
        print("\033[1;31m[!] Invalid or Expired OTP.\033[0m")
    except PasswordHashInvalid:
        print("\033[1;31m[!] Invalid 2FA Password.\033[0m")
    except FloodWait as e:
        print(f"\033[1;31m[!] FloodWait: Please wait {e.value} seconds.\033[0m")
    except Exception as e:
        print(f"\033[1;31m[!] Error: {e}\033[0m")
    finally:
        if client.is_connected:
            await client.disconnect()

async def generate_telethon_cli():
    print("\n\033[1;33m--- Telethon Session Generation ---\033[0m")
    api_id_raw = input("Enter API_ID (from my.telegram.org): ").strip()
    if not api_id_raw.isdigit():
        print("\033[1;31m[!] Invalid API_ID. Must be numbers.\033[0m")
        return
    api_id = int(api_id_raw)
    api_hash = input("Enter API_HASH: ").strip()

    mode = input("Select Type [1] User Account  [2] Bot Token MTProto: ").strip()
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    if mode == "2":
        bot_token = input("Enter BOT_TOKEN (from @BotFather): ").strip()
        try:
            await client.start(bot_token=bot_token)
            session = client.session.save()
            me = await client.get_me()
            print("\n\033[1;32m[✓] Telethon Bot Session Generated Successfully!\033[0m")
            print(f"Bot: @{me.username} ({me.id})\n")
            print(f"\033[1;37m{session}\033[0m\n")
        except Exception as e:
            print(f"\033[1;31m[!] Error: {e}\033[0m")
        finally:
            if client.is_connected():
                await client.disconnect()
        return

    phone = input("Enter Phone Number (with country code, e.g. +1234567890): ").strip()
    try:
        await client.connect()
        send_result = await client.send_code_request(phone)
        otp = input("Enter OTP Code sent to Telegram: ").strip().replace(" ", "").replace("-", "")
        
        try:
            await client.sign_in(phone, otp, phone_code_hash=send_result.phone_code_hash)
        except SessionPasswordNeededError:
            password = getpass.getpass("Enter 2FA Password: ").strip()
            await client.sign_in(password=password)
            
        session = client.session.save()
        me = await client.get_me()
        print("\n\033[1;32m[✓] Telethon Session Generated Successfully!\033[0m")
        print(f"User: {me.first_name} (@{me.username or 'No Username'}) | ID: {me.id}\n")
        print("\033[1;33m--- YOUR SESSION STRING (DO NOT SHARE) ---\033[0m")
        print(f"\033[1;37m{session}\033[0m\n")
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        print("\033[1;31m[!] Invalid or Expired OTP.\033[0m")
    except PasswordHashInvalidError:
        print("\033[1;31m[!] Invalid 2FA Password.\033[0m")
    except FloodWaitError as e:
        print(f"\033[1;31m[!] FloodWait: Please wait {e.seconds} seconds.\033[0m")
    except Exception as e:
        print(f"\033[1;31m[!] Error: {e}\033[0m")
    finally:
        if client.is_connected():
            await client.disconnect()

def main():
    print_banner()
    print("Select Library:")
    print(" [1] Pyrogram v2 (Recommended for Modern Bots)")
    print(" [2] Telethon (Legacy & Multi-thread Bots)")
    print(" [0] Exit")
    
    choice = input("\nEnter choice [1/2/0]: ").strip()
    if choice == "1":
        asyncio.run(generate_pyrogram_cli())
    elif choice == "2":
        asyncio.run(generate_telethon_cli())
    elif choice == "0":
        sys.exit(0)
    else:
        print("Invalid option selected.")

if __name__ == "__main__":
    main()
