
# network/client.py
import socket
import struct
import uuid
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from .file_utils import encrypt_file_to_bytes
from .core.rsa_utils import load_private_key, get_private_key_path, get_public_key_path
from cryptography.exceptions import InvalidSignature

class FileClient:
    def __init__(self, server_ip, port=5000):
        self.server_ip = server_ip
        self.port = port
        self.sock = None
        
    def send_file(self, file_path, progress_callback=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if progress_callback:
                progress_callback(5, "连接服务器...")
            
            self.sock.connect((self.server_ip, self.port))
            
            if progress_callback:
                progress_callback(10, "已连接到服务器")
            
            server_pub_key = self._exchange_keys()
            
            if progress_callback:
                progress_callback(15, "密钥交换成功")
            
            if progress_callback:
                progress_callback(20, "读取文件...")
            
            sender_private_key = load_private_key(get_private_key_path())
            
            if progress_callback:
                progress_callback(25, "加密文件...")
            
            package_data = encrypt_file_to_bytes(file_path, server_pub_key, sender_private_key)
            
            if progress_callback:
                progress_callback(60, "文件加密完成")
            
            header = struct.pack(">I", len(package_data))
            
            if progress_callback:
                progress_callback(65, "发送数据...")
            
            total_sent = 0
            data_to_send = header + package_data
            chunk_size = 64 * 1024
            
            while total_sent < len(data_to_send):
                chunk = data_to_send[total_sent:total_sent + chunk_size]
                self.sock.send(chunk)
                total_sent += len(chunk)
                
                progress = 65 + int((total_sent / len(data_to_send)) * 30)
                if progress_callback and progress <= 95:
                    progress_callback(min(progress, 95), f"发送中 {total_sent}/{len(data_to_send)}")
            
            if progress_callback:
                progress_callback(98, "发送完成")
            
            print(f"文件发送成功，数据包大小: {len(package_data)} bytes")
            
            if progress_callback:
                progress_callback(100, "传输完成")
            
        except FileNotFoundError as e:
            if progress_callback:
                progress_callback(0, f"文件错误: {e}")
            print(f"文件错误: 找不到文件 - {e}")
            raise
        except ConnectionError as e:
            if progress_callback:
                progress_callback(0, f"网络错误: {e}")
            print(f"网络错误: 连接失败 - {e}")
            raise
        except socket.error as e:
            if progress_callback:
                progress_callback(0, f"套接字错误: {e}")
            print(f"套接字错误: {e}")
            raise
        except InvalidSignature as e:
            if progress_callback:
                progress_callback(0, f"安全错误: {e}")
            print(f"安全错误: 签名验证失败 - {e}")
            raise
        except ValueError as e:
            if progress_callback:
                progress_callback(0, f"数据错误: {e}")
            print(f"数据错误: {e}")
            raise
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"未知错误: {e}")
            print(f"未知错误: {type(e).__name__} - {e}")
            raise
        finally:
            if self.sock:
                self.sock.close()
    
    def _exchange_keys(self):
        try:
            key_size_bytes = self._recv_exact(4)
            key_size = struct.unpack(">I", key_size_bytes)[0]
            server_pub_pem = self._recv_exact(key_size)
            
            server_pub_key = serialization.load_pem_public_key(
                server_pub_pem,
                backend=default_backend()
            )
            
            with open(get_public_key_path(), "rb") as f:
                pub_key = f.read()
                self.sock.sendall(struct.pack(">I", len(pub_key)) + pub_key)
            
            return server_pub_key
        except FileNotFoundError:
            raise RuntimeError("客户端公钥文件未找到，请先生成密钥对")
    
    def _recv_exact(self, n):
        data = bytearray()
        while len(data) < n:
            packet = self.sock.recv(n - len(data))
            if not packet:
                raise ConnectionError("连接提前关闭")
            data.extend(packet)
        return bytes(data)
