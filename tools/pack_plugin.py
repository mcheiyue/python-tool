"""打包 / 校验 / 生成密钥 —— Tool Bundle v2 (.mcy) 维护者工具。

用法：
  生成新密钥对（打印私钥与对应公钥，私钥绝不入库）：
      python tools/pack_plugin.py --gen-key

  校验一个 .mcy（验签 + 打印 tool_id 与解压顶层目录名）：
      python tools/pack_plugin.py --verify <文件.mcy>

  打包（需先设置 MCY_SIGNING_KEY）：
      set MCY_SIGNING_KEY=<Ed25519 私钥 hex（64 字符）>
      python tools/pack_plugin.py <源目录> <输出文件> [tool_id]

Tool ID: 0=Ghostscript, 1=Pandoc, 2=LibreOffice（默认 0）。该字段当前仅作
元数据记录，加载器不据此决定解压位置——解压后的顶层目录名由 TAR 内容决定，
因此源目录必须命名为工具名（如 pandoc/、ghostscript/）。

打包完成后会自动打印「私钥对应公钥 vs 源内嵌公钥」比对：两者不一致时，
该私钥签出的包将无法通过内置校验——历史上曾因内嵌公钥抄错导致全部包被拒。
"""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.bundles.format import (
    BUNDLE_PUBLIC_KEY,
    read_bundle,
)


def load_private_key() -> Ed25519PrivateKey:
    key_hex = os.environ.get("MCY_SIGNING_KEY", "").strip()
    if not key_hex:
        raise SystemExit(
            "缺少环境变量 MCY_SIGNING_KEY（Ed25519 私钥 hex，64 字符）。\n"
            "生成密钥对：python tools/pack_plugin.py --gen-key\n"
            "私钥由维护者离线保管，绝不提交到仓库。"
        )
    try:
        raw = bytes.fromhex(key_hex)
    except ValueError as e:
        raise SystemExit(f"MCY_SIGNING_KEY 不是合法 hex: {e}")
    if len(raw) != 32:
        raise SystemExit(f"MCY_SIGNING_KEY 必须为 32 字节（64 个 hex 字符），当前 {len(raw)} 字节")
    return Ed25519PrivateKey.from_private_bytes(raw)


def _public_key_b64(public_key) -> str:
    """Ed25519 公钥的 Raw 32 字节 base64（与 core/bundles/format.py 同格式）。"""
    raw = public_key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return base64.b64encode(raw).decode()


def _embedded_public_b64() -> str:
    return _public_key_b64(BUNDLE_PUBLIC_KEY)


def _report_key_match(private_key: Ed25519PrivateKey) -> bool:
    """比对私钥推导公钥与源内嵌公钥，返回是否一致。"""
    derived = _public_key_b64(private_key.public_key())
    embedded = _embedded_public_b64()
    if derived == embedded:
        print("[key] 私钥对应公钥与源内嵌公钥一致 OK")
        return True
    print("[key] WARNING 私钥对应公钥与源内嵌公钥不一致！")
    print(f"  源内嵌    : {embedded}")
    print(f"  私钥推导  : {derived}")
    print("  该私钥签出的包将无法通过内置校验（除非另行提供公钥）。")
    return False


def cmd_gen_key():
    key = Ed25519PrivateKey.generate()
    private_hex = key.private_bytes_raw().hex()
    public_b64 = _public_key_b64(key.public_key())
    embedded = _embedded_public_b64()
    print("已生成新的 Ed25519 密钥对：")
    print()
    print("  私钥（离线保管，绝不提交到仓库/日志/CI）:")
    print(f"    {private_hex}")
    print()
    print("  公钥（需替换 core/bundles/format.py 的 _BUNDLE_PUBLIC_KEY_B64）:")
    print(f"    {public_b64}")
    print()
    if public_b64 == embedded:
        print("  注意：这与当前源内嵌公钥相同（重新生成了同一对？概率极低）。")
    else:
        print(f"  当前源内嵌公钥: {embedded}")
        print("  更换公钥会使此前分发的全部 .mcy 作废，需重新打包。")


def cmd_verify(path: str):
    tool_id, tar_data = read_bundle(path, BUNDLE_PUBLIC_KEY)
    size_mb = os.path.getsize(path) / 1024 / 1024
    tar_mb = len(tar_data) / 1024 / 1024
    print(f"[verify] {path}")
    print(f"  签名校验 : 通过（内嵌官方公钥）")
    print(f"  tool_id  : {tool_id}")
    print(f"  包体     : {size_mb:.2f} MB -> tar {tar_mb:.2f} MB")
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r") as tar:
        names = tar.getnames()
    if names:
        root = names[0].split('/')[0].split('\\')[0]
        print(f"  解压顶层 : {root}/  （消费方按此目录名定位可执行文件）")
    return tool_id


def cmd_pack(source: str, output: str, tool_id: int):
    if not os.path.isdir(source):
        raise SystemExit(f"源目录不存在: {source}")

    key = load_private_key()
    _report_key_match(key)

    print(f"Packing {source} -> {output} (tool_id={tool_id})...")
    from core.bundles.format import pack_bundle
    pack_bundle(source, output, tool_id, key)
    print(f"Done! Created {output} ({os.path.getsize(output) / 1024 / 1024:.2f} MB)")


def main():
    args = sys.argv[1:]

    if args and args[0] == "--gen-key":
        cmd_gen_key()
        return

    if args and args[0] == "--verify":
        if len(args) < 2:
            raise SystemExit("用法: python tools/pack_plugin.py --verify <文件.mcy>")
        if not os.path.exists(args[1]):
            raise SystemExit(f"文件不存在: {args[1]}")
        cmd_verify(args[1])
        return

    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    source, output = args[0], args[1]
    tid = int(args[2]) if len(args) > 2 else 0
    cmd_pack(source, output, tid)


if __name__ == "__main__":
    main()
