import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from reportlab.pdfbase import pdfmetrics
from app import export_builder as eb

FAIL = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        FAIL.append(name)


print("\n1. Sog'lom mashina (shrift o'rnatilgan)")
check("muammo yo'q deb aytadi", eb.verify_pdf_fonts() == [], str(eb.verify_pdf_fonts()))

print("\n2. Shrift umuman ro'yxatdan o'tmagan (Linux, fonts-dejavu-core yo'q)")
real_names = pdfmetrics.getRegisteredFontNames
pdfmetrics.getRegisteredFontNames = lambda: ["Helvetica", "Courier"]
try:
    out = eb.verify_pdf_fonts()
    check("muammo aniqlandi", len(out) == 1, f"{len(out)} ta")
    check("sababi aytilgan", out and "never registered" in out[0])
    check("yechimi aytilgan", out and "fonts-dejavu-core" in out[0], out[0][:80] if out else "")
finally:
    pdfmetrics.getRegisteredFontNames = real_names

print("\n3. Shrift bor, lekin tojik harflarini chizmaydi (masalan Vera)")
real_getfont = pdfmetrics.getFont


class _FakeFace:
    charToGlyph = {ord(c): i + 1 for i, c in enumerate(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя")}


class _FakeFont:
    face = _FakeFace()


pdfmetrics.getFont = lambda name: _FakeFont()
try:
    out = eb.verify_pdf_fonts()
    check("muammo aniqlandi", len(out) == 1, f"{len(out)} ta")
    check("qaysi harflar yo'qligi aytilgan",
          out and all(c in out[0] for c in "ғқҳҷӣӯ"), out[0][:100] if out else "")
    check("ruscha harflar ayblanmagan", out and "а" not in out[0].split("draw ")[1][:8])
finally:
    pdfmetrics.getFont = real_getfont

print("\n4. Tekshiruvning o'zi yiqilsa, startupni o'ldirmaydi")
pdfmetrics.getFont = lambda name: (_ for _ in ()).throw(RuntimeError("bo'm"))
try:
    out = eb.verify_pdf_fonts()
    check("xato ushlandi, exception chiqmadi", len(out) == 1)
    check("nima bo'lgani yozilgan", out and "could not verify" in out[0])
finally:
    pdfmetrics.getFont = real_getfont

print("\n5. Sog'lom holatga qaytdi")
check("yana toza", eb.verify_pdf_fonts() == [])

print()
if FAIL:
    print(f"{len(FAIL)} FAILED: {FAIL}")
    sys.exit(1)
print("tekshiruv haqiqatan ishlaydi")
