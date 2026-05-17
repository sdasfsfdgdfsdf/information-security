
# network/core/aes_utils.py

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature, InvalidTag
import os
import struct
from io import BytesIO

GCM_TAG_SIZE = 16

def aes_encrypt_file(input_file, output_file=None):
    with open(input_file, 'rb') as f:
        file_data = f.read()
    
    encrypted_data, key = aes_encrypt_data(file_data)
    
    if output_file:
        with open(output_file, 'wb') as f:
            f.write(encrypted_data)
        with open("key.bin", 'wb') as key_file:
            key_file.write(key)
    
    return encrypted_data, key


def aes_encrypt_data(data):
    key = os.urandom(32)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = PKCS7(algorithms.AES.block_size).padder()

    encrypted_data = encryptor.update(padder.update(data) + padder.finalize()) + encryptor.finalize()
    tag = encryptor.tag
    
    buffer = BytesIO()
    buffer.write(iv)
    buffer.write(tag)
    buffer.write(encrypted_data)
    
    print(f"AES-GCM加密完成，已附加认证标签 (IV:{len(iv)}B, Tag:{len(tag)}B, Data:{len(encrypted_data)}B)")
    return buffer.getvalue(), key


def aes_decrypt_file(input_file, key_path, output_file=None):
    with open(input_file, 'rb') as f:
        encrypted_data = f.read()
    with open(key_path, 'rb') as f:
        key = f.read()
    
    decrypted_data = aes_decrypt_data(encrypted_data, key)
    
    if output_file:
        with open(output_file, 'wb') as f:
            f.write(decrypted_data)
    
    return decrypted_data


def aes_decrypt_data(encrypted_data, key):
    if len(encrypted_data) < 16 + GCM_TAG_SIZE:
        raise ValueError("加密数据长度不足")
    
    buffer = BytesIO(encrypted_data)
    
    iv = buffer.read(16)
    tag = buffer.read(GCM_TAG_SIZE)
    ciphertext = buffer.read()
    
    print(f"AES-GCM解密中 (IV:{len(iv)}B, Tag:{len(tag)}B, Ciphertext:{len(ciphertext)}B)")
    
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    
    try:
        decrypted = decryptor.update(ciphertext) + decryptor.finalize()
    except InvalidTag:
        print("AES-GCM认证标签验证失败，数据可能被篡改")
        raise InvalidSignature("AES-GCM认证标签验证失败，数据可能被篡改")
    
    unpadder = PKCS7(algorithms.AES.block_size).unpadder()
    unpadded = unpadder.update(decrypted) + unpadder.finalize()
    
    print("AES-GCM解密完成，认证标签验证通过")
    return unpadded
