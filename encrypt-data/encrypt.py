import os
import zipfile
import hashlib
import logging
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers import modes, Cipher
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import shutil
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s: %(asctime)s [%(levelname)s] [%(funcName)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("encrypt.log"),
    ],
)
logger = logging.getLogger(__name__)


class Encryptor:
    def __init__(self):
        pass

    def compress_and_encrypt(self, folder_path: str, pwd: str, delete_original: bool):
        zip_file_path = self.__create_zip_archive(folder_path)

        if not zip_file_path:
            logger.error("ZIP archive creation failed. Aborting encryption.")
            return

        # Generate key, iv, and salt
        key, iv, salt = self.__generate_key(pwd, os.urandom(16), os.urandom(16))

        # Pass all three to encrypt_file
        self.__encrypt_file(zip_file_path, key, iv, salt)

        print(f"dell orig: {delete_original}")
        if delete_original:
            shutil.rmtree(folder_path)

        return

    def decrypt_and_uncompress(self, file_path: str, pwd: str):
        # Use the new decrypt_file method that takes just the file_path and pwd
        decrypted_file_path = self.__decrypt_file(file_path, pwd)

        if not decrypted_file_path:
            logger.error("Decryption failed. Cannot extract files.")
            return

        try:
            with zipfile.ZipFile(decrypted_file_path, "r") as zipf:
                zipf.extractall(os.path.dirname(decrypted_file_path))

            os.remove(decrypted_file_path)
        except Exception as e:
            logger.error(f"Error extracting ZIP archive: {e}")

    def __pad(self, data: bytes) -> bytes:
        """Pads the data using PKCS7 padding."""
        padder = padding.PKCS7(AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        return padded_data

    def __unpad(self, data: bytes) -> bytes:
        """Removes PKCS7 padding from the data."""
        unpadder = padding.PKCS7(AES.block_size).unpadder()
        unpadded_data = unpadder.update(data) + unpadder.finalize()
        return unpadded_data

    def __create_zip_archive(self, folder_path: str):
        """Compress folder into a zip file"""
        folder_path = Path(folder_path)
        zip_file_path = folder_path.parent / f"{folder_path.name}.zip"

        try:
            with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(
                            file_path,
                            os.path.relpath(file_path, folder_path),
                        )
            logger.info(f"Created ZIP archive at {zip_file_path}")
            return str(zip_file_path)
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {e}")
            return None

    def __generate_key(
        self, pwd: str, salt: bytes, iv: bytes
    ) -> tuple[bytes, bytes, bytes]:
        """Generates a key, IV, and salt from a password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = kdf.derive(pwd.encode())

        return key, iv, salt

    def __encrypt_file(self, file_path: str, key: bytes, iv: bytes, salt: bytes):
        encrypted_file_path = file_path + ".enc"
        try:
            with open(file_path, "rb") as file:
                data = file.read()
                cipher = Cipher(AES(key), modes.CBC(iv))
                encryptor = cipher.encryptor()
                padded_data = self.__pad(data)
                encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

            # Write salt and IV at the beginning of the file
            with open(encrypted_file_path, "wb") as file:
                file.write(salt + iv + encrypted_data)

            os.remove(file_path)
            logger.info(f"Encrypted file saved at {encrypted_file_path}")
            return encrypted_file_path
        except Exception as e:
            logger.error(f"Error encrypting file: {e}")
            return None

    def __decrypt_file(self, file_path: str, pwd: str) -> str:
        decrypted_zip_path = file_path[:-4]  # Remove .enc extension
        try:
            with open(file_path, "rb") as f:
                data = f.read()

                salt = data[:16]
                iv = data[16:32]
                encrypted_data = data[32:]

                key, _, _ = self.__generate_key(pwd, salt, iv)

                cipher = Cipher(AES(key), modes.CBC(iv))
                decryptor = cipher.decryptor()
                decrypted_padded_data = (
                    decryptor.update(encrypted_data) + decryptor.finalize()
                )
                unpadded_data = self.__unpad(decrypted_padded_data)

            with open(decrypted_zip_path, "wb") as f:
                f.write(unpadded_data)

            logger.info(f"Decrypted file saved at {decrypted_zip_path}")
            return decrypted_zip_path
        except Exception as e:
            logger.error(f"Error decrypting file: {e}")
            return None
