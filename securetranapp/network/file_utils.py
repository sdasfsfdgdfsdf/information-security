
from .core.rsa_utils import load_private_key, rsa_encrypt_data, rsa_decrypt_data
from .core.aes_utils import aes_encrypt_data, aes_decrypt_data
from .core.signature import sign_data, verify_signature
from cryptography.exceptions import InvalidSignature

SEPARATOR = b"<SEPARATOR>"

def encrypt_file_to_bytes(file_path, receiver_pub_key, sender_private_key):
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    encrypted_data, aes_key = aes_encrypt_data(file_data)
    print("AES加密成功")
    
    encrypted_aes_key = rsa_encrypt_data(aes_key, receiver_pub_key)
    print("AES密钥RSA加密成功")
    
    signature = sign_data(file_data, sender_private_key)
    print("签名成功")
    
    package = (
        encrypted_aes_key + 
        SEPARATOR + 
        signature + 
        SEPARATOR + 
        encrypted_data
    )
    
    print(f"文件加密完成，数据包大小: {len(package)} bytes")
    return package


def decrypt_file_from_bytes(package_data, receiver_private_key, sender_public_key):
    parts = package_data.split(SEPARATOR)
    
    if len(parts) != 3:
        raise ValueError(f"数据包格式错误，期望3部分，实际{len(parts)}部分")
    
    encrypted_aes_key = parts[0]
    signature = parts[1]
    encrypted_data = parts[2]
    print("数据包分离完成")
    
    aes_key = rsa_decrypt_data(encrypted_aes_key, receiver_private_key)
    print("AES密钥解密成功")
    
    decrypted_data = aes_decrypt_data(encrypted_data, aes_key)
    print("AES数据解密成功")
    
    is_valid = verify_signature(sender_public_key, decrypted_data, signature)
    
    if not is_valid:
        raise InvalidSignature("签名验证失败，文件可能被篡改")
    
    print("签名验证成功！文件完整且来源可信")
    return decrypted_data
