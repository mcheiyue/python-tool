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
    _extracted_cache = {}  # 缓存已解压的插件路径 {mcy_path: extracted_path}

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
            # 获取 libs/.temp 目录
            from core.utils.resource_path import get_app_root
            base = get_app_root()
            
            temp_root = os.path.join(base, "libs", ".temp")
            
            if os.path.exists(temp_root):
                # 尝试清理旧的临时目录
                # 注意：如果其他实例正在运行，且锁定了文件，删除会失败（Windows下），这是预期的安全行为
                shutil.rmtree(temp_root, ignore_errors=True)
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

        # 检查缓存
        if mcy_path in self._extracted_cache:
            path = self._extracted_cache[mcy_path]
            if os.path.exists(path):
                return path
            else:
                del self._extracted_cache[mcy_path]

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
            # 获取项目根目录
            from core.utils.resource_path import get_app_root
            base = get_app_root()

            if persistent:
                target_base = os.path.join(base, "libs")
            else:
                # 临时目录：libs/.temp/session_xxxx
                libs_temp = os.path.join(base, "libs", ".temp")
                if not os.path.exists(libs_temp):
                    os.makedirs(libs_temp, exist_ok=True)
                
                # 在 .temp 下创建唯一的临时目录
                target_base = tempfile.mkdtemp(dir=libs_temp, prefix="session_")
                self._temp_dirs.append(target_base)
            
            if not os.path.exists(target_base):
                os.makedirs(target_base, exist_ok=True)

            # 4. 解包 TAR
            import io
            tar_buffer = io.BytesIO(tar_data)
            with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
                tar.extractall(path=target_base)
                
                # 获取解压出的顶层目录名（通常是 ghostscript 或 pandoc）
                members = tar.getnames()
                final_path = target_base
                if members:
                    root_dir = members[0].split('/')[0].split('\\')[0]
                    final_path = os.path.join(target_base, root_dir)
                
                # 存入缓存
                self._extracted_cache[mcy_path] = final_path
                return final_path

        except Exception as e:
            print(f"Failed to load plugin: {e}")
            return None

# 全局单例
loader = PluginLoader()
