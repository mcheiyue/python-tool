"""外部工具 zip 包加载器（预置包 / manifest 下载产物）。

模块沿革：core/plugin_loader.py → Tool Bundle (.mcy) 加载器 → 本模块。
按 ADR-0003 修订版（分发模型转向 Manifest + 预置包），签名体系整体退场：
信任锚是 plugins/manifest.json 中的 sha256，由 core/tools/downloader.py 在
下载时校验；本模块只做路径安全审查与解压。
"""
import os
import atexit
import shutil
import zipfile
import tempfile

from core.utils.logger import AppLogger


class SecurityError(Exception):
    """zip 解压安全相关异常"""
    pass


class BundleLoader:
    _instance = None
    _temp_dirs = []

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
            from core.utils.resource_path import get_data_root
            temp_root = os.path.join(get_data_root(), "libs", ".temp")

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
        """路径审查：所有成员必须落在 target_base 内。"""
        target_base_abs = os.path.abspath(target_base)

        for name in names:
            member_path_abs = os.path.abspath(os.path.join(target_base, name))

            if not member_path_abs.startswith(target_base_abs + os.sep) and member_path_abs != target_base_abs:
                raise SecurityError(f"路径穿越攻击检测: {name}")

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

        temporary → libs/.temp/session_*（atexit 清理）；
        persistent → libs/<subdir>/（subdir=工具名时）。
        SecurityError 向外抛给调用方。

        解压后把「唯一顶层目录」的内容提升到目标根：官方 zip 顶层名带版本
        （pandoc-3.12.1/），不归一化的话持久模式会落到带版本号的目录，
        与发现链的 libs/<工具名>/ 布局不符，导致每次启动重复解压。
        """
        from core.utils.resource_path import get_data_root
        base = get_data_root()

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

    def _temp_root(self) -> str:
        """libs/.temp 根目录（临时解压与下载暂存共用），不存在则创建。"""
        from core.utils.resource_path import get_data_root
        root = os.path.join(get_data_root(), "libs", ".temp")
        if not os.path.exists(root):
            os.makedirs(root, exist_ok=True)
        return root


# 全局单例
loader = BundleLoader()
