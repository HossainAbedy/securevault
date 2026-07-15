"""
build_xpi.py — Package browser_extension_firefox/ as a .xpi file.
A .xpi is just a ZIP with a different extension.
Run from the installer/ folder or project root.
"""
import zipfile
from pathlib import Path


def build_xpi(project_root: Path) -> Path:
    src = project_root / "browser_extension_firefox"
    out = project_root / "installer" / "dist" / "securevault_firefox.xpi"
    out.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"Firefox extension folder not found: {src}")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                zf.write(f, f.relative_to(src))

    size_kb = out.stat().st_size // 1024
    print(f"  ✓ Firefox .xpi built: {out}  ({size_kb} KB)")
    return out


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    build_xpi(root)
