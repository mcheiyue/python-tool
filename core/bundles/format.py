"""Tool Bundle v2 (.mcy) 格式：LZMA 压缩 + Ed25519 签名。

v2 放弃 AES 加密（打包对象是开源二进制，保密无意义），改为对压缩载荷做
Ed25519 签名：私钥由维护者离线持有、绝不入库；验证公钥内嵌本模块。
格式头 VERSION=2，v1 不再读取（见 ADR-0003）。

本模块只做打包/校验/解包，不做 TAR 路径安全检查——那由加载器
的 _safe_extract 负责（符号链接/路径穿越拒绝）。
"""
import io
import os
import lzma
import struct
import tarfile
import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature

MAGIC_HEADER = b"MCY\x00"
VERSION = 2

# 验证公钥（base64，Raw 32 字节）。私钥由维护者离线持有，绝不入库。
# 更换公钥 = 旧 .mcy 全部作废并重打包；因此它是一个长期不变的契约常量。
_BUNDLE_PUBLIC_KEY_B64 = "ssI7WIr52icPp+QUV+tXJYdN4nYO/huzrM8kNVJCgwU="
BUNDLE_PUBLIC_KEY = Ed25519PublicKey.from_public_bytes(
    base64.b64decode(_BUNDLE_PUBLIC_KEY_B64)
)

# v2 布局：MAGIC(4) | VERSION(1) | TOOL_ID(1) | REST_SIZE(8) | SIGNATURE(64) | COMPRESSED_DATA
# REST_SIZE = 签名 + 压缩载荷的总字节数
_HEADER_STRUCT = struct.Struct("<4sBBQ")
SIGNATURE_SIZE = 64
# 前缀仅指固定头（14 字节）；签名与载荷同属 rest，长度由 REST_SIZE 声明
_PREFIX_SIZE = _HEADER_STRUCT.size


class BundleFormatError(ValueError):
    """Tool Bundle 格式/签名相关异常。"""


def sign_data(private_key: Ed25519PrivateKey, data: bytes) -> bytes:
    return private_key.sign(data)


def verify_signature(public_key: Ed25519PublicKey, signature: bytes, data: bytes) -> None:
    try:
        public_key.verify(signature, data)
    except InvalidSignature as e:
        raise BundleFormatError("Tool Bundle 签名校验失败（文件可能被篡改）") from e


def pack_bundle(source_dir: str, output_file: str, tool_id: int,
                private_key: Ed25519PrivateKey) -> None:
    """打包为 v2 .mcy：TAR -> LZMA -> Ed25519 签名 -> 落盘。"""
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    tar_data = tar_buffer.getvalue()

    compressed = lzma.compress(tar_data, preset=9)
    signature = sign_data(private_key, compressed)

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "wb") as f:
        # 字段语义 = 前缀之后的总字节数（签名 + 压缩载荷），与 read_bundle 的两次 read 对齐
        f.write(_HEADER_STRUCT.pack(
            MAGIC_HEADER, VERSION, tool_id, SIGNATURE_SIZE + len(compressed)
        ))
        f.write(signature)
        f.write(compressed)


def read_bundle(path: str, public_key: Ed25519PublicKey) -> tuple[int, bytes]:
    """读取并校验 v2 .mcy，返回 (tool_id, 解压后的 TAR 字节)。

    v1 文件（VERSION=1）与签名不符一律拒绝，不做兼容回退。
    """
    with open(path, "rb") as f:
        prefix = f.read(_PREFIX_SIZE)
        if len(prefix) < _PREFIX_SIZE:
            raise BundleFormatError("Tool Bundle 文件过短")

        magic, version, tool_id, rest_size = _HEADER_STRUCT.unpack_from(prefix)
        if magic != MAGIC_HEADER:
            raise BundleFormatError("Invalid plugin file format")
        if version != VERSION:
            raise BundleFormatError(
                f"不支持的 Tool Bundle 版本 {version}（当前仅支持 v{VERSION}）"
            )

        # 字段语义 = 签名 + 压缩载荷的总长；读满后切分，长度不符即文件损坏
        rest = f.read(rest_size)
        if len(rest) != rest_size:
            raise BundleFormatError("Tool Bundle 数据不完整")
        signature = rest[:SIGNATURE_SIZE]
        compressed = rest[SIGNATURE_SIZE:]

    verify_signature(public_key, signature, compressed)
    try:
        tar_data = lzma.decompress(compressed)
    except lzma.LZMAError as e:
        raise BundleFormatError(f"Tool Bundle 解压失败: {e}") from e

    return tool_id, tar_data
