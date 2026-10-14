"""打包 Tool Bundle v2 (.mcy)。

用法（维护者，离线持有私钥）：
    set MCY_SIGNING_KEY=<Ed25519 私钥 hex（64 字符）>
    python tools/pack_plugin.py <源目录> <输出文件> [tool_id]

Tool ID: 0=Ghostscript, 1=Pandoc（默认 0）。

私钥绝不入库；验证公钥内嵌 core/bundles/format.py（更换公钥=旧包全部作废）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.bundles.format import pack_bundle


def load_private_key() -> Ed25519PrivateKey:
    key_hex = os.environ.get("MCY_SIGNING_KEY", "").strip()
    if not key_hex:
        raise SystemExit(
            "缺少环境变量 MCY_SIGNING_KEY（Ed25519 私钥 hex，64 字符）。\n"
            "私钥由维护者离线保管，绝不提交到仓库。"
        )
    try:
        raw = bytes.fromhex(key_hex)
    except ValueError as e:
        raise SystemExit(f"MCY_SIGNING_KEY 不是合法 hex: {e}")
    if len(raw) != 32:
        raise SystemExit(f"MCY_SIGNING_KEY 必须为 32 字节（64 个 hex 字符），当前 {len(raw)} 字节")
    return Ed25519PrivateKey.from_private_bytes(raw)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    source = sys.argv[1]
    output = sys.argv[2]
    tid = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    if not os.path.isdir(source):
        raise SystemExit(f"源目录不存在: {source}")

    key = load_private_key()
    print(f"Packing {source} -> {output} (tool_id={tid})...")
    pack_bundle(source, output, tid, key)
    print(f"Done! Created {output} ({os.path.getsize(output) / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
