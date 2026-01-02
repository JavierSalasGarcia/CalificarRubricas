from pathlib import Path

root = Path(r"C:\Users\javie\OneDrive - Universidad Autónoma del Estado de México\MCI-2025B Instrumentación Electrónica - Submitted files")

# Listar archivos
for p in root.rglob("*"):
    if p.is_file():
        print(p)

# Probar lectura simple (ejemplo: txt)
txts = list(root.rglob("*.txt"))
if txts:
    with open(txts[0], "r", encoding="utf-8", errors="ignore") as f:
        print(f.read(500))
