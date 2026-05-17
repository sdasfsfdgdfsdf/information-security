
# network/server.py
import socket
import threading
import struct
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from .file_utils import decrypt_file_from_bytes
from .core.rsa_utils import load_private_key, get_private_key_path, get_public_key_path
from .core.aes_utils import aes_decrypt_data
from cryptography.exceptions import InvalidSignature, InvalidTag

class FileServer:
    def __init__(self, host='0.0.0.0', port=5000, progress_callback=None):
        self.host = host
        self.port = port
        self.progress_callback = progress_callback
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def start(self):
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
            print(f"服务器监听中 {self.host}:{self.port}")
            
            while True:
                conn, addr = self.sock.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
        except socket.error as e:
            print(f"服务器启动失败: {e}")
            raise
        except Exception as e:
            print(f"服务器异常: {type(e).__name__} - {e}")
            raise
        finally:
            self.sock.close()

            
    def handle_client(self, conn, addr):
        try:
            print(f"收到来自 {addr} 的连接")
            
            if self.progress_callback:
                self.progress_callback(5, "接收连接...")
            
            peer_pub_key = self._exchange_keys(conn)
            
            if self.progress_callback:
                self.progress_callback(10, "密钥交换完成")
            
            if self.progress_callback:
                self.progress_callback(15, "接收数据...")
            
            header = self._recv_exact(conn, 4)
            data_size = struct.unpack(">I", header)[0]
            print(f"接收数据包大小: {data_size} bytes")
            
            if self.progress_callback:
                self.progress_callback(20, f"准备接收 {data_size} bytes...")
            
            package_data = self._recv_exact_with_progress(conn, data_size)
            
            if self.progress_callback:
                self.progress_callback(50, "数据接收完成")
            
            if self.progress_callback:
                self.progress_callback(55, "加载密钥...")
            
            receiver_private_key = load_private_key(get_private_key_path())
            
            if self.progress_callback:
                self.progress_callback(60, "解密文件...")
            
            try:
                decrypted_data = decrypt_file_from_bytes(
                    package_data, 
                    receiver_private_key, 
                    peer_pub_key
                )
                
                if self.progress_callback:
                    self.progress_callback(85, "解密完成")
                
                original_filename = self._extract_filename_from_decrypted(decrypted_data)
                output_file = f"received_{original_filename}"
                
                if self.progress_callback:
                    self.progress_callback(90, f"保存文件 {output_file}...")
                
                with open(output_file, 'wb') as f:
                    f.write(decrypted_data)
                
                print(f"文件解密成功，已保存为: {output_file}")
                
                if self.progress_callback:
                    self.progress_callback(100, f"接收完成: {output_file}")
                
            except InvalidSignature as e:
                print(f"安全警告: 签名验证失败 - {e}")
                if self.progress_callback:
                    self.progress_callback(0, f"签名验证失败")
                raise
            except InvalidTag as e:
                print(f"安全警告: AES-GCM标签验证失败 - {e}")
                if self.progress_callback:
                    self.progress_callback(0, f"AES-GCM标签验证失败")
                raise
                
        except ConnectionError as e:
            if self.progress_callback:
                self.progress_callback(0, f"连接异常: {e}")
            print(f"网络错误: 连接异常 - {e}")
        except FileNotFoundError as e:
            if self.progress_callback:
                self.progress_callback(0, f"文件错误: {e}")
            print(f"文件错误: {e}")
        except socket.error as e:
            if self.progress_callback:
                self.progress_callback(0, f"套接字错误: {e}")
            print(f"套接字错误: {e}")
        except ValueError as e:
            if self.progress_callback:
                self.progress_callback(0, f"数据错误: {e}")
            print(f"数据错误: {e}")
        except Exception as e:
            if self.progress_callback:
                self.progress_callback(0, f"未知错误: {e}")
            print(f"未知错误: {type(e).__name__} - {e}")
        finally:
            conn.close()
    
    def _extract_filename_from_decrypted(self, decrypted_data):
        if not decrypted_data:
            return "decrypted_file"
        
        original_filename = "decrypted_file"
        
        if decrypted_data.startswith(b'\x89PNG\r\n\x1a\n'):
            original_filename = "decrypted_file.png"
        elif decrypted_data.startswith(b'\xff\xd8\xff'):
            original_filename = "decrypted_file.jpg"
        elif decrypted_data.startswith(b'GIF87a') or decrypted_data.startswith(b'GIF89a'):
            original_filename = "decrypted_file.gif"
        elif decrypted_data.startswith(b'%PDF'):
            original_filename = "decrypted_file.pdf"
        elif decrypted_data.startswith(b'PK\x03\x04'):
            original_filename = "decrypted_file.zip"
        elif decrypted_data[:20].isascii() and len(decrypted_data) > 4:
            for ext in [b'.txt', b'.doc', b'.docx', b'.pdf', b'.xls', b'.xlsx', b'.ppt', b'.pptx']:
                if decrypted_data[:100].find(ext) != -1:
                    original_filename = f"decrypted_file{ext.decode()}"
                    break
        
        return original_filename
    
    def _recv_exact_with_progress(self, conn, n):
        data = bytearray()
        total_received = 0
        chunk_size = 64 * 1024
        
        while total_received < n:
            remaining = n - total_received
            packet = conn.recv(min(chunk_size, remaining))
            if not packet:
                raise ConnectionError("连接提前关闭")
            data.extend(packet)
            total_received += len(packet)
            
            if self.progress_callback:
                progress = 20 + int((total_received / n) * 30)
                self.progress_callback(min(progress, 49), f"接收中 {total_received}/{n}")
        
        return bytes(data)
    
    def _exchange_keys(self, conn):
        try:
            with open(get_public_key_path(), "rb") as f:
                pub_key = f.read()
                conn.sendall(struct.pack(">I", len(pub_key)) + pub_key)
            
            key_size_bytes = self._recv_exact(conn, 4)
            key_size = struct.unpack(">I", key_size_bytes)[0]
            client_pub_pem = self._recv_exact(conn, key_size)
            
            return serialization.load_pem_public_key(
                client_pub_pem,
                backend=default_backend()
            )
            
        except FileNotFoundError:
            raise RuntimeError("服务器公钥文件未找到，请先生成密钥对")
    
    def _recv_exact(self, conn, n):
        data = bytearray()
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                raise ConnectionError("连接提前关闭")
            data.extend(packet)
        return bytes(data)
