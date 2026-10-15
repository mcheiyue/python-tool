"""Tool Bundle (.mcy) 加载器（v2）。

原 core/plugin_loader.py：按 ADR-0002 改名，按 ADR-0003 改接 v2 签名格式
（读取/验签/解压委托 core.bundles.format.read_bundle；路径安全检查保留在本模块）。
"""
import os
import atexit
import shutil
import tarfile
import zipfile
import tempfile

from core.bundles.format import (
    BUNDLE_PUBLIC_KEY,
    BundleFormatError,
    stream_bundle,
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

    def _validate_member_paths(self, names, target_base):
        """路径审查：所有成员必须落在 target_base 内（tar/zip 共用）。"""
        target_base_abs = os.path.abspath(target_base)

        for name in names:
            member_path_abs = os.path.abspath(os.path.join(target_base, name))

            # 检查路径是否在目标目录内
            if not member_path_abs.startswith(target_base_abs + os.sep) and member_path_abs != target_base_abs:
                raise SecurityError(f"路径穿越攻击检测: {name}")

    def _safe_extract(self, tar, target_base):
        """
        安全解压 TAR 文件，防止路径穿越攻击
        :param tar: tarfile.TarFile 对象
        :param target_base: 目标解压目录
        """
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise SecurityError(f"符号链接/硬链接成员被拒绝: {member.name}")

        self._validate_member_paths([m.name for m in tar.getmembers()], target_base)

        # 所有路径验证通过，执行解压
        tar.extractall(path=target_base)

    def _safe_extract_zip(self, zip_file, target_base):
        """安全解压 ZIP：链接成员（external_attr 中的 S_IFLNK）与路径穿越均拒绝。

        zip 没有 islnk 概念，符号链接只能从 external_attr 高位识别——
        不检查的话 Linux/macOS 构建的上游包可能带链接成员。
        """
        infos = zip_file.infolist()
        for info in infos:
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise SecurityError(f"符号链接成员被拒绝: {info.filename}")

        self._validate_member_paths([i.filename for i in infos], target_base)

        zip_file.extractall(target_base)

    def extract_zip(self, zip_path, persistent=False, subdir=None):
        """安全解压上游官方 zip，返回解压目录。

        模式与 extract_bundle 一致：temporary → libs/.temp/session_*
        （atexit 清理），persistent → libs/<subdir>/（subdir=工具名时）。
        SecurityError 向外抛给调用方。

        解压后把「唯一顶层目录」的内容提升到目标根：官方 zip 顶层名带版本
        （pandoc-3.12.1/），不归一化的话持久模式会落到带版本号的目录，
        与发现链的 libs/<工具名>/ 布局不符，导致每次启动重复解压。
        """
        from core.utils.resource_path import get_app_root
        base = get_app_root()

        if persistent:
            target_base = os.path.join(base, "libs", subdir) if subdir \
                else os.path.join(base, "libs")
        else:
            target_base = tempfile.mkdtemp(prefix="session_", dir=self._temp_root())
            self._temp_dirs.append(target_base)

        if not os.path.exists(target_base):
            os.makedirs(target_base, exist_ok=True)

        with zipfile.ZipFile(zip_path) as zf:
            self._safe_extract_zip(zf, target_base)
            names = zf.namelist()

        self._flatten_single_toplevel(target_base, names)
        return target_base

    @staticmethod
    def _flatten_single_toplevel(target_base, names):
        """zip 唯一顶层是目录时，把其内容提升到 target_base（抹掉版本名层）。"""
        tops = {n.split('/')[0].split('\\')[0] for n in names if n.strip('/')}
        if len(tops) != 1:
            return
        root = tops.pop()
        root_dir = os.path.join(target_base, root)
        if not os.path.isdir(root_dir):
            return
        for entry in os.listdir(root_dir):
            shutil.move(os.path.join(root_dir, entry),
                        os.path.join(target_base, entry))
        os.rmdir(root_dir)

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

        staged_tar = None
        try:
            # 1. 流式加载 v2 头 + 验签 + LZMA 解压（v1 与签名不符在此拒绝）
            tool_id, staged_tar = self._stage_and_verify(
                bundle_path, public_key or BUNDLE_PUBLIC_KEY
            )

            # 2. 确定目标目录
            from core.utils.resource_path import get_app_root
            base = get_app_root()

            if persistent:
                target_base = os.path.join(base, "libs")
            else:
                # 临时目录：libs/.temp/session_xxxx
                target_base = tempfile.mkdtemp(prefix="session_", dir=self._temp_root())
                self._temp_dirs.append(target_base)

            if not os.path.exists(target_base):
                os.makedirs(target_base, exist_ok=True)

            # 3. 解包 TAR（安全检查：防止路径穿越攻击）
            with tarfile.open(staged_tar, mode="r") as tar:
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
        finally:
            if staged_tar:
                self._remove_staged(staged_tar)

    def _temp_root(self) -> str:
        """libs/.temp 根目录（分阶段文件与临时解压共用），不存在则创建。"""
        from core.utils.resource_path import get_app_root
        root = os.path.join(get_app_root(), "libs", ".temp")
        if not os.path.exists(root):
            os.makedirs(root, exist_ok=True)
        return root

    def _stage_and_verify(self, bundle_path: str, public_key):
        """流式解压到分阶段文件并完成验签，返回 (tool_id, 分阶段 tar 路径)。

        分阶段文件是解压后的 TAR（与解压结果同体积），单独放在 libs/.temp/stage_*
        并登记清理；内存占用不随包体积增长。
        """
        stage_dir = tempfile.mkdtemp(prefix="stage_", dir=self._temp_root())
        self._temp_dirs.append(stage_dir)
        staged_tar = os.path.join(stage_dir, "bundle.tar")
        try:
            tool_id = stream_bundle(bundle_path, staged_tar, public_key)
        except Exception:
            self._remove_staged(staged_tar)
            raise
        return tool_id, staged_tar

    @staticmethod
    def _remove_staged(staged_tar):
        """删除分阶段 tar 及其所属的 stage_ 目录（目录为空才算清理干净）。"""
        try:
            os.remove(staged_tar)
            stage_dir = os.path.dirname(staged_tar)
            if os.path.basename(stage_dir).startswith("stage_") and not os.listdir(stage_dir):
                os.rmdir(stage_dir)
        except OSError:
            pass


# 全局单例
loader = BundleLoader()
