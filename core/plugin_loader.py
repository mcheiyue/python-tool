import os
import sys
import struct
import tarfile
import lzma
import hashlib
import tempfile
import shutil
import atexit
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# 必须与打包工具保持一致
SECRET_KEY_SEED = b"PythonTool-Plugin-Secret-Key-2024"
SECRET_KEY = hashlib.sha256(SECRET_KEY_SEED).digest()
MAGIC_HEADER = b"MCY\x00"

class PluginLoader:
    _instance = None
    _temp_dirs = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginLoader, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化清理机制"""
        atexit.register(self.cleanup)
        self._clean_stale_temps()

    def _clean_stale_temps(self):
        """清理上次未正常退出留下的临时目录"""
        try:
            temp_base = tempfile.gettempdir()
            for item in os.listdir(temp_base):
                if item.startswith("pytool_libs_"):
                    path = os.path.join(temp_base, item)
                    if os.path.isdir(path):
                        try:
                            shutil.rmtree(path, ignore_errors=True)
                        except Exception:
                            pass
        except Exception:
            pass

    def cleanup(self):
        """清理本次会话的临时目录"""
        for d in self._temp_dirs:
            try:
                if os.path.exists(d):
                    shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        self._temp_dirs.clear()

    def _decrypt_data(self, iv, encrypted_data):
        """解密数据"""
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # 去除 PKCS7 填充
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data

    def extract_plugin(self, mcy_path, persistent=False):
        """
        解压插件
        :param mcy_path: .mcy 文件路径
        :param persistent: 是否持久化解压（True=解压到libs目录，False=解压到临时目录）
        :return: 解压后的目录路径
        """
        if not os.path.exists(mcy_path):
            raise FileNotFoundError(f"Plugin file not found: {mcy_path}")

        try:
            with open(mcy_path, "rb") as f:
                # 校验 Header
                header = f.read(4)
                if header != MAGIC_HEADER:
                    raise ValueError("Invalid plugin file format")
                
                version = struct.unpack("B", f.read(1))[0]
                tool_id = struct.unpack("B", f.read(1))[0]
                original_size = struct.unpack("Q", f.read(8))[0]
                
                iv = f.read(16)
                encrypted_data = f.read()
            
            # 1. 解密
            compressed_data = self._decrypt_data(iv, encrypted_data)
            
            # 2. 解压 LZMA
            tar_data = lzma.decompress(compressed_data)
            
            # 3. 确定目标目录
            if persistent:
                # 获取项目根目录下的 libs
                if getattr(sys, 'frozen', False):
                    base = os.path.dirname(sys.executable)
                else:
                    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                target_base = os.path.join(base, "libs")
            else:
                # 临时目录
                target_base = tempfile.mkdtemp(prefix="pytool_libs_")
                self._temp_dirs.append(target_base)
            
            if not os.path.exists(target_base):
                os.makedirs(target_base)

            # 4. 解包 TAR
            import io
            tar_buffer = io.BytesIO(tar_data)
            with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
                tar.extractall(path=target_base)
                
                # 获取解压出的顶层目录名（通常是 ghostscript 或 pandoc）
                members = tar.getnames()
                if members:
                    root_dir = members[0].split('/')[0].split('\\')[0]
                    return os.path.join(target_base, root_dir)
                return target_base

        except Exception as e:
            print(f"Failed to load plugin: {e}")
            return None

# 全局单例
loader = PluginLoader()
