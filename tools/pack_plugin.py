import os
import sys
import struct
import tarfile
import lzma
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# 硬编码的密钥，实际使用中应妥善保管
# 这里使用 SHA-256 派生一个 32 字节的密钥
SECRET_KEY_SEED = b"PythonTool-Plugin-Secret-Key-2024"
SECRET_KEY = hashlib.sha256(SECRET_KEY_SEED).digest()

MAGIC_HEADER = b"MCY\x00"
VERSION = 1

def encrypt_data(data):
    """使用 AES-256-CBC 加密数据"""
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # PKCS7 填充
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()
    
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    return iv, encrypted_data

def pack_plugin(source_dir, output_file, tool_id):
    """
    打包插件
    :param source_dir: 源目录
    :param output_file: 输出文件 (.mcy)
    :param tool_id: 工具ID (0=GS, 1=Pandoc)
    """
    print(f"Packing {source_dir} -> {output_file}...")
    
    # 1. 创建内存中的 TAR 包
    import io
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    
    tar_data = tar_buffer.getvalue()
    original_size = len(tar_data)
    print(f"  Original TAR size: {original_size / 1024 / 1024:.2f} MB")
    
    # 2. LZMA 压缩
    print("  Compressing with LZMA (preset=9)...")
    compressed_data = lzma.compress(tar_data, preset=9)
    print(f"  Compressed size: {len(compressed_data) / 1024 / 1024:.2f} MB")
    
    # 3. AES 加密
    print("  Encrypting...")
    iv, encrypted_data = encrypt_data(compressed_data)
    
    # 4. 写入文件
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    
    with open(output_file, "wb") as f:
        # Header
        f.write(MAGIC_HEADER)
        f.write(struct.pack("B", VERSION))
        f.write(struct.pack("B", tool_id))
        f.write(struct.pack("Q", original_size)) # 8 bytes unsigned long long
        
        # IV
        f.write(iv)
        
        # Data
        f.write(encrypted_data)
        
    print(f"Done! Created {output_file} ({os.path.getsize(output_file) / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pack_plugin.py <source_dir> <output_file> [tool_id]")
        print("Tool IDs: 0=Ghostscript, 1=Pandoc")
        sys.exit(1)
        
    source = sys.argv[1]
    output = sys.argv[2]
    tid = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    pack_plugin(source, output, tid)
