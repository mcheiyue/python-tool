"""Tool Bundle (.mcy) 加载器（v2）。

原 core/plugin_loader.py：按 ADR-0002 改名，按 ADR-0003 改接 v2 签名格式
（读取/验签/解压委托 core.bundles.format.read_bundle；路径安全检查保留在本模块）。
"""
import io
import os
import atexit
import shutil
import tarfile
import tempfile

from core.bundles.format import (
    BUNDLE_PUBLIC_KEY,
    BundleFormatError,
    read_bundle,
)
from core.utils.logger import AppLogger, timed_operation


class SecurityError(Exception):
    """Tool Bundle 解压安全相关异常"""
    pass


class BundleLoader:
    _instance = None
    _temp_dirs = []
    _extracted_cache = {}  # 缓存已解压的插件路径 {bundle_path: extracted_path}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BundleLoader, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化清理机制"""
        self.logger = AppLogger()
        atexit.register(self.cleanup)
        self._clean_stale_temps()
        self.logger.info("BundleLoader 初始化完成")

    def _clean_stale_temps(self):
        """清理上次未正常退出留下的临时目录"""
        try:
            from core.utils.resource_path import get_app_root
            temp_root = os.path.join(get_app_root(), "libs", ".temp")

            if os.path.exists(temp_root):
                # 如果其他实例正在运行且锁定了文件，删除会失败（Windows下），这是预期的安全行为
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

    def _safe_extract(self, tar, target_base):
        """
        安全解压 TAR 文件，防止路径穿越攻击
        :param tar: tarfile.TarFile 对象
        :param target_base: 目标解压目录
        """
        target_base_abs = os.path.abspath(target_base)

        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise SecurityError(f"符号链接/硬链接成员被拒绝: {member.name}")
            # 计算成员的绝对路径
            member_path = os.path.join(target_base, member.name)
            member_path_abs = os.path.abspath(member_path)

            # 检查路径是否在目标目录内
            if not member_path_abs.startswith(target_base_abs + os.sep) and member_path_abs != target_base_abs:
                raise SecurityError(f"路径穿越攻击检测: {member.name}")

        # 所有路径验证通过，执行解压
        tar.extractall(path=target_base)

    @timed_operation("Tool Bundle 解压")
    def extract_bundle(self, bundle_path, persistent=False, public_key=None):
        """
        解压 Tool Bundle
        :param bundle_path: .mcy 文件路径
        :param persistent: 是否持久化解压（True=解压到libs目录，False=解压到临时目录）
        :param public_key: 验签公钥（None=内置默认公钥；测试/第三方签名可注入，b2 留位）
        :return: 解压后的目录路径；格式/签名失败返回 None（与 v1 行为一致）
        """
        if not os.path.exists(bundle_path):
            self.logger.error(f"Tool Bundle 文件不存在: {bundle_path}")
            raise FileNotFoundError(f"Bundle file not found: {bundle_path}")

        # 检查缓存
        if bundle_path in self._extracted_cache:
            path = self._extracted_cache[bundle_path]
            if os.path.exists(path):
                self.logger.debug(f"使用缓存的插件路径: {path}")
                return path
            else:
                del self._extracted_cache[bundle_path]

        self.logger.info(f"开始解压 Tool Bundle: {os.path.basename(bundle_path)}, 模式: {'持久' if persistent else '临时'}")

        try:
            # 1. 读取 v2 头 + 验签 + LZMA 解压（v1 与签名不符在此拒绝）
            _tool_id, tar_data = read_bundle(bundle_path, public_key or BUNDLE_PUBLIC_KEY)

            # 2. 确定目标目录
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

            # 3. 解包 TAR（安全检查：防止路径穿越攻击）
            tar_buffer = io.BytesIO(tar_data)
            with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
                # 安全检查：验证所有成员路径，防止路径穿越
                self._safe_extract(tar, target_base)

                # 获取解压出的顶层目录名（通常是 ghostscript 或 pandoc）
                members = tar.getnames()
                final_path = target_base
                if members:
                    root_dir = members[0].split('/')[0].split('\\')[0]
                    final_path = os.path.join(target_base, root_dir)

                # 存入缓存
                self._extracted_cache[bundle_path] = final_path
                self.logger.info(f"Tool Bundle 解压成功: {final_path}")
                return final_path

        except SecurityError as e:
            self.logger.error(f"安全检查失败: {e}")
            raise
        except BundleFormatError as e:
            self.logger.error(f"Tool Bundle 校验失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Tool Bundle 加载失败: {e}")
            return None


# 全局单例
loader = BundleLoader()
