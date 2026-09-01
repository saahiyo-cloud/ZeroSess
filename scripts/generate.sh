#!/usr/bin/env bash
# ZeroSess - 1-Line Termux / Linux Session String Generator
set -e

echo -e "\033[1;36m"
echo "  ⚡ ZeroSess Fast Setup & Generator"
echo "  Zero-PII • In-Memory • Pyrogram v2 & Telethon"
echo -e "\033[0m"

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo -e "\033[1;33m[!] Python3 is required. Installing...\033[0m"
    if command -v pkg &> /dev/null; then
        pkg update -y && pkg install python git -y
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update -y && sudo apt-get install python3 python3-pip git -y
    else
        echo -e "\033[1;31m[-] Please install Python 3 manually.\033[0m"
        exit 1
    fi
fi

# Clone or run in temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo -e "\033[1;32m[+] Downloading ZeroSess runner...\033[0m"
git clone --depth 1 https://github.com/saahiyo-cloud/ZeroSess.git .

echo -e "\033[1;32m[+] Installing required dependencies...\033[0m"
pip install -r requirements.txt --quiet --no-warn-script-location || pip3 install -r requirements.txt --quiet

echo -e "\033[1;32m[+] Starting Interactive Wizard...\033[0m"
python3 -m bot.cli

# Clean up
cd ~
rm -rf "$TEMP_DIR"
