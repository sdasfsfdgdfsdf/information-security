
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from io import BytesIO
import os
import getpass

def get_key_dir():
    key_dir = os.path.join(os.path.expanduser("~"), ".securetranapp")
    os.makedirs(key_dir, exist_ok=True)
    return key_dir

def get_private_key_path():
    return os.path.join(get_key_dir(), "private_key.pem")

def get_public_key_path():
    return os.path.join(get_key_dir(), "public_key.pem")

def generate_keypair(key_size=2048):
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

def save_key(key, filename, is_private=True):
    if is_private:
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    else:
        pem = key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    with open(filename, 'wb') as f:
        f.write(pem)

def load_private_key(filename):
    with open(filename, 'rb') as f:
        return serialization.load_pem_private_key(
            f.read(),
            backend=default_backend(),
            password=None
        )

def load_public_key(filename):
    with open(filename, 'rb') as f:
        return serialization.load_pem_public_key(
            f.read(),
            backend=default_backend()
        )

def rsa_encrypt_data(data, public_key, chunk_size=190):
    buffer = BytesIO()
    offset = 0
    
    while offset < len(data):
        chunk = data[offset:offset + chunk_size]
        encrypted = public_key.encrypt(
            chunk,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        buffer.write(len(encrypted).to_bytes(4, 'big'))
        buffer.write(encrypted)
        offset += chunk_size
    
    print("RSA加密完成")
    return buffer.getvalue()


def rsa_decrypt_data(encrypted_data, private_key):
    buffer = BytesIO(encrypted_data)
    decrypted_data = bytearray()
    
    while True:
        len_bytes = buffer.read(4)
        if not len_bytes or len(len_bytes) < 4:
            break
        chunk_len = int.from_bytes(len_bytes, 'big')
        encrypted = buffer.read(chunk_len)
        
        if not encrypted or len(encrypted) < chunk_len:
            break
            
        decrypted = private_key.decrypt(
            encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        decrypted_data.extend(decrypted)
    
    print("RSA解密完成")
    return bytes(decrypted_data)
