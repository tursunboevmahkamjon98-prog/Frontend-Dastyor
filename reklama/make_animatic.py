"""Rahnamo reklama: 30 soniyalik qoralama video (animatik), 1080x1920.

Har bir kadr ssenariydagi vaqtida, tojikcha subtitr va ekran yozuvlari bilan.
O'qituvchi suratga olinadigan kadrlarda nima olinishi yozilgan joy bor;
telefon ekrani (3-4) va yakuniy kadr (8) tayyor ko'rinishda chizilgan.

Ishga tushirish:  python make_animatic.py   (Pillow va ffmpeg kerak)
"""
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build")
LOGO = os.path.join(HERE, "..", "public", "logo.png")
FONT_B = "C:/Windows/Fonts/segoeuib.ttf"
FONT_R = "C:/Windows/Fonts/segoeui.ttf"
RED = (220, 38, 38)


def font(size, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size)


def gradient(top, bottom):
    img = Image.new("RGB", (W, H), top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def wrap(d, text, f, width):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if d.textlength(test, font=f) <= width:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def centered(d, y, text, f, fill, width=W - 160, spacing=14):
    for line in wrap(d, text, f, width):
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y), line, font=f, fill=fill)
        y += f.size + spacing
    return y


def badge(d, n, span):
    """Small crew label: which shot and when (Uzbek, for the film crew)."""
    txt = f"QORALAMA  \u00b7  Kadr {n}/8  \u00b7  {span}"
    f = font(30)
    w = d.textlength(txt, font=f)
    d.rounded_rectangle([40, 50, 40 + w + 40, 110], 30, fill=(0, 0, 0, 150))
    d.text((60, 60), txt, font=f, fill=(255, 255, 255))


def pill(d, text, y, bg=RED, fg=(255, 255, 255), size=58):
    f = font(size)
    w = d.textlength(text, font=f)
    x = (W - w) / 2
    d.rounded_rectangle([x - 40, y, x + w + 40, y + size + 44], 40, fill=bg)
    d.text((x, y + 14), text, font=f, fill=fg)


def subtitle(d, text):
    """Tajik spoken line, Reels-style, in the lower third."""
    f = font(64)
    lines = [l for part in text.split("\n") for l in wrap(d, part, f, W - 200)]
    lh = f.size + 16
    top = H - 520 - len(lines) * lh
    widest = max(d.textlength(l, font=f) for l in lines)
    d.rounded_rectangle([(W - widest) / 2 - 36, top - 28, (W + widest) / 2 + 36, top + len(lines) * lh + 20],
                        28, fill=(0, 0, 0, 175))
    for i, l in enumerate(lines):
        w = d.textlength(l, font=f)
        d.text(((W - w) / 2, top + i * lh), l, font=f, fill=(255, 255, 255))


def placeholder(d, title, notes, dark=True):
    """Where real footage of the teacher goes, with what to film (Uzbek)."""
    box = [90, 330, W - 90, 1180]
    col = (255, 255, 255, 120) if dark else (120, 60, 60, 140)
    # dashed border
    x0, y0, x1, y1 = box
    for x in range(x0, x1, 40):
        d.line([(x, y0), (min(x + 22, x1), y0)], fill=col, width=5)
        d.line([(x, y1), (min(x + 22, x1), y1)], fill=col, width=5)
    for y in range(y0, y1, 40):
        d.line([(x0, y), (x0, min(y + 22, y1))], fill=col, width=5)
        d.line([(x1, y), (x1, min(y + 22, y1))], fill=col, width=5)
    fg = (255, 255, 255) if dark else (60, 30, 30)
    sub = (210, 215, 235) if dark else (110, 80, 80)
    y = centered(d, y0 + 70, "BU YERDA SURAT:", font(34), sub)
    y = centered(d, y + 10, title, font(58), fg, width=W - 320)
    y += 30
    for n in notes:
        y = centered(d, y, "\u2022 " + n, font(38, bold=False), sub, width=W - 300, spacing=8) + 10


def save(img, path):
    img.convert("RGB").save(path)


def night_bg():
    img = gradient((8, 14, 40), (30, 40, 85)).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W - 520, 260, W + 120, 900], fill=(255, 190, 90, 70))
    return Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(120)))


def day_bg():
    return gradient((255, 246, 240), (255, 226, 214)).convert("RGBA")


def layer(base):
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return over, ImageDraw.Draw(over)


def phone(d, screen_draw):
    """A phone mock-up; screen_draw(d, x0, y0, x1, y1) fills the screen."""
    x0, y0, x1, y1 = 190, 300, W - 190, 1500
    d.rounded_rectangle([x0, y0, x1, y1], 80, fill=(20, 20, 24))
    sx0, sy0, sx1, sy1 = x0 + 28, y0 + 28, x1 - 28, y1 - 28
    d.rounded_rectangle([sx0, sy0, sx1, sy1], 58, fill=(255, 255, 255))
    d.rounded_rectangle([(x0 + x1) / 2 - 80, y0 + 44, (x0 + x1) / 2 + 80, y0 + 74], 15, fill=(20, 20, 24))
    screen_draw(d, sx0, sy0, sx1, sy1)


def app_header(d, sx0, sy0, sx1, logo_small):
    d.rectangle([sx0, sy0 + 60, sx1, sy0 + 170], fill=(255, 255, 255))
    return logo_small, (int(sx0 + 40), int(sy0 + 85))


def check_circle(d, cx, cy, r=26):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(22, 163, 74))
    d.line([(cx - 12, cy + 1), (cx - 3, cy + 10), (cx + 13, cy - 9)], fill=(255, 255, 255), width=7)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    logo = Image.open(LOGO).convert("RGBA")
    logo_small = logo.resize((70, 70))
    clips = []  # (folder, frame count)

    def still(name, img, seconds):
        folder = os.path.join(OUT, name)
        os.makedirs(folder)
        save(img, os.path.join(folder, "f0000.png"))
        clips.append((name, seconds, "still"))

    def seq(name, frames, seconds):
        folder = os.path.join(OUT, name)
        os.makedirs(folder)
        for i, img in enumerate(frames):
            save(img, os.path.join(folder, f"f{i:04d}.png"))
        clips.append((name, seconds, "seq"))

    # 1 — night, tired teacher
    base = night_bg()
    o, d = layer(base)
    badge(d, 1, "0\u20133 s")
    pill(d, "\u0421\u043e\u0430\u0442\u0438 23:40", 170, bg=(255, 255, 255), fg=(20, 25, 60))
    placeholder(d, "O'qituvchi yuzi yaqindan, charchagan",
                ["stol chirog'i yuzni yoritadi", "daftarlar uyumi, qizil ruchka", "ko'zini ishqalaydi"])
    subtitle(d, "\u0411\u043e\u0437 \u0442\u043e \u043d\u0438\u0441\u0444\u0438 \u0448\u0430\u0431 \u043a\u043e\u043d\u0441\u043f\u0435\u043a\u0442 \u043c\u0435\u043d\u0430\u0432\u0438\u0441\u0430\u043c...")
    still("s1", Image.alpha_composite(base, o), 3)

    # 2 — daughter at the door
    base = night_bg()
    o, d = layer(base)
    badge(d, 2, "3\u20136 s")
    placeholder(d, "Eshikda qizi mo'ralaydi",
                ["o'qituvchi yelkasi ortidan olinadi", "qizi pijamada, ajablanib qaraydi"])
    subtitle(d, "\u041c\u043e\u0434\u0430\u0440, \u0448\u0443\u043c\u043e \u04b3\u0430\u043d\u04ef\u0437 Rahnamo-\u0440\u043e \u043d\u0430\u043c\u0435\u0434\u043e\u043d\u0435\u0434?")
    still("s2", Image.alpha_composite(base, o), 3)

    # 3 — typing the topic (animated)
    topic = "\u0424\u043e\u0442\u043e\u0441\u0438\u043d\u0442\u0435\u0437, \u0441\u0438\u043d\u0444\u0438 7"
    frames = []
    total = 3 * FPS
    for i in range(total):
        base = night_bg()
        o, d = layer(base)
        badge(d, 3, "6\u20139 s")
        n = min(len(topic), int(i / (total * 0.7) * len(topic)) + 1)
        pressed = i > total * 0.82

        def screen(d, sx0, sy0, sx1, sy1, n=n, pressed=pressed):
            o.paste(logo_small, (int(sx0 + 40), int(sy0 + 80)), logo_small)
            d.text((sx0 + 130, sy0 + 88), "Rahnamo", font=font(46), fill=(30, 30, 30))
            d.text((sx0 + 40, sy0 + 230), "\u041c\u0430\u0432\u0437\u04ef\u0438 \u0434\u0430\u0440\u0441", font=font(40), fill=(90, 90, 90))
            d.rounded_rectangle([sx0 + 40, sy0 + 300, sx1 - 40, sy0 + 410], 24, outline=RED, width=5, fill=(255, 250, 250))
            caret = "|" if (i // 8) % 2 == 0 else ""
            d.text((sx0 + 70, sy0 + 327), topic[:n] + caret, font=font(46, bold=False), fill=(25, 25, 25))
            bcol = (185, 28, 28) if pressed else RED
            d.rounded_rectangle([sx0 + 40, sy0 + 470, sx1 - 40, sy0 + 580], 28, fill=bcol)
            label = "\u0421\u043e\u0445\u0442\u0430\u043d"
            fw = d.textlength(label, font=font(48))
            d.text(((sx0 + sx1 - fw) / 2, sy0 + 492), label, font=font(48), fill=(255, 255, 255))

        phone(d, screen)
        pill(d, "\u041c\u0430\u0432\u0437\u04ef\u0438 \u0434\u0430\u0440\u0441\u0440\u043e \u043d\u0430\u0432\u0438\u0441\u0435\u0434", 1560)
        frames.append(Image.alpha_composite(base, o))
    seq("s3", frames, 3)

    # 4 — materials appear one by one (animated)
    items = ["\u041a\u043e\u043d\u0441\u043f\u0435\u043a\u0442", "\u0422\u0435\u0441\u0442",
             "\u041f\u0440\u0435\u0437\u0435\u043d\u0442\u0430\u0442\u0441\u0438\u044f"]
    frames = []
    total = 3 * FPS
    for i in range(total):
        base = night_bg()
        o, d = layer(base)
        badge(d, 4, "9\u201312 s")
        shown = min(3, i // 22 + 1)

        def screen(d, sx0, sy0, sx1, sy1, shown=shown):
            o.paste(logo_small, (int(sx0 + 40), int(sy0 + 80)), logo_small)
            d.text((sx0 + 130, sy0 + 88), "Rahnamo", font=font(46), fill=(30, 30, 30))
            d.text((sx0 + 40, sy0 + 220), "\u0424\u043e\u0442\u043e\u0441\u0438\u043d\u0442\u0435\u0437, \u0441\u0438\u043d\u0444\u0438 7", font=font(40), fill=(90, 90, 90))
            for k in range(shown):
                y = sy0 + 310 + k * 190
                d.rounded_rectangle([sx0 + 40, y, sx1 - 40, y + 160], 28, fill=(255, 245, 244), outline=(245, 205, 205), width=3)
                check_circle(d, sx0 + 110, y + 80)
                d.text((sx0 + 165, y + 52), items[k], font=font(44), fill=(30, 30, 30))

        phone(d, screen)
        pill(d, "1 \u0434\u0430\u049b\u0438\u049b\u0430", 1560, size=72)
        frames.append(Image.alpha_composite(base, o))
    seq("s4", frames, 3)

    # 5 — surprised face
    base = night_bg()
    o, d = layer(base)
    badge(d, 5, "12\u201314 s")
    placeholder(d, "Hayratlangan yuz, juda yaqindan",
                ["qo'li bilan og'zini yopadi", "montajda tez zoom bo'ladi"])
    subtitle(d, "\u0427\u04e3?! \u0414\u0430\u0440 \u044f\u043a \u0434\u0430\u049b\u0438\u049b\u0430?!")
    still("s5", Image.alpha_composite(base, o), 2)

    # 6 — classroom next day
    base = day_bg()
    o, d = layer(base)
    badge(d, 6, "14\u201320 s")
    pill(d, "\u041a\u043e\u043d\u0441\u043f\u0435\u043a\u0442 \u00b7 \u0422\u0435\u0441\u0442 \u00b7 \u041f\u0440\u0435\u0437\u0435\u043d\u0442\u0430\u0442\u0441\u0438\u044f", 170, size=50)
    placeholder(d, "Sinf: o'qituvchi tetik, kameraga qaraydi",
                ["doskada mavzu, ekranda prezentatsiya", "o'quvchilar qo'l ko'taradi",
                 "avval umumiy sinf, keyin beldan yuqori"], dark=False)
    subtitle(d, "\u041a\u043e\u043d\u0441\u043f\u0435\u043a\u0442, \u0442\u0435\u0441\u0442, \u043f\u0440\u0435\u0437\u0435\u043d\u0442\u0430\u0442\u0441\u0438\u044f \u2014 \u04b3\u0430\u043c\u0430\u0430\u0448\u0440\u043e Rahnamo \u0442\u0430\u0439\u0451\u0440 \u043c\u0435\u043a\u0443\u043d\u0430\u0434.")
    still("s6", Image.alpha_composite(base, o), 6)

    # 7 — 21:00, the joke
    base = night_bg()
    o, d = layer(base)
    badge(d, 7, "20\u201325 s")
    pill(d, "\u0421\u043e\u0430\u0442\u0438 21:00", 170, bg=(255, 255, 255), fg=(20, 25, 60))
    placeholder(d, "Uy, kechqurun: ikkalasi kadrda",
                ["turmush o'rtog'i hayron so'raydi", "o'qituvchi jilmayadi, chiroqni o'chiradi"])
    subtitle(d, "\u2014 \u0422\u0443 \u043a\u043e\u043d\u0441\u043f\u0435\u043a\u0442 \u043d\u0430\u0432\u0438\u0448\u0442\u04e3?\n\u2014 Rahnamo \u043d\u0430\u0432\u0438\u0448\u0442!")
    still("s7", Image.alpha_composite(base, o), 5)

    # 8 — end card (final quality)
    base = gradient((235, 40, 40), (165, 20, 28)).convert("RGBA")
    o, d = layer(base)
    card = [W / 2 - 230, 430, W / 2 + 230, 890]
    d.rounded_rectangle(card, 90, fill=(255, 255, 255))
    big = logo.resize((360, 360))
    o.paste(big, (int(W / 2 - 180), 480), big)
    centered(d, 980, "Rahnamo", font(130), (255, 255, 255))
    centered(d, 1140, "\u0434\u0430\u0441\u0442\u0451\u0440\u0438 \u043c\u0443\u0430\u043b\u043b\u0438\u043c", font(64, bold=False), (255, 225, 225))
    pill(d, "\u0420\u043e\u0439\u0433\u043e\u043d \u0441\u0430\u043d\u04b7\u0435\u0434!", 1340, bg=(255, 255, 255), fg=(200, 25, 30), size=72)
    centered(d, 1560, "\u041a\u043e\u043d\u0441\u043f\u0435\u043a\u0442 \u00b7 \u0422\u0435\u0441\u0442 \u00b7 \u041f\u0440\u0435\u0437\u0435\u043d\u0442\u0430\u0442\u0441\u0438\u044f \u00b7 \u041b\u0435\u043a\u0441\u0438\u044f",
             font(42, bold=False), (255, 235, 235))
    still("s8", Image.alpha_composite(base, o), 5)

    # Encode each clip (stills get a slow push-in), then join.
    parts = []
    for name, seconds, kind in clips:
        src = os.path.join(OUT, name)
        dst = os.path.join(OUT, name + ".mp4")
        frames = seconds * FPS
        if kind == "still":
            vf = (f"scale={W * 2}:{H * 2},zoompan=z='1+0.04*on/{frames}':d={frames}"
                  f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(src, "f0000.png"),
                   "-vf", vf, "-frames:v", str(frames)]
        else:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                   "-i", os.path.join(src, "f%04d.png"), "-frames:v", str(frames)]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), dst]
        subprocess.run(cmd, check=True)
        parts.append(dst)

    lst = os.path.join(OUT, "list.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for p in parts:
            fh.write(f"file '{p.replace(os.sep, '/')}'\n")
    final = os.path.join(HERE, "dastyor_reklama_qoralama.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart", final],
                   check=True)
    print("OK", final)


if __name__ == "__main__":
    main()
