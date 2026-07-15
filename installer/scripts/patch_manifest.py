from pathlib import Path
import sys

if len(sys.argv) != 3:
    print("Usage:")
    print("python patch_manifest.py <template> <output>")
    sys.exit(1)

template = Path(sys.argv[1])
output = Path(sys.argv[2])

host_path = r"C:\Program Files\SecureVault\native_host\native_host.exe"

text = template.read_text(encoding="utf-8")
text = text.replace("__HOST_PATH__", host_path.replace("\\", "\\\\"))

output.write_text(text, encoding="utf-8")

print(f"Generated: {output}")
