"""应用版本的单一来源：读仓库根 VERSION 文件。其他消费方都从这里取，勿在别处写死。"""
import os

from core.utils.resource_path import get_resource_path

FALLBACK = "0.0.0"


def get_app_version() -> str:
    try:
        with open(get_resource_path("VERSION"), encoding="utf-8") as f:
            version = f.read().strip()
    except OSError:
        return FALLBACK
    return version or FALLBACK
