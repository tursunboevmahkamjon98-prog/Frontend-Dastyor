# Dastyor backend — miqyoslash va xavfsizlik rejasi

**Maqsad:** ~5 000 ro'yxatdan o'tgan o'qituvchi, cho'qqida 100–200 bir vaqtda faol.
**Holat:** reja. Kod o'zgarishi bosqichma-bosqich, har bosqich alohida tekshiriladi.
**Sana:** 2026-09-11. Asos: `ea52953` commit.

---

## 1. Yuklamani to'g'ri tushunish

"100–200 bir vaqtda" degani "200 ta generatsiya bir vaqtda" degani emas. Bu backendda
so'rovlar uch xil, va ular butunlay boshqa resursni yeydi:

| Sinf | Misol | Davomiyligi | Nimaga bog'liq |
|---|---|---|---|
| **Arzon** | login, ro'yxat, `/stats`, `/search` | 5–50 ms | Postgres |
| **AI** | `/generate`, `/generate-all` | **10–180 s** | Cerebras'ning **umumiy** TPM kvotasi |
| **Render** | `/download-docx`, `/download-pptx`, `/download-pdf` | 1–5 s | **CPU** (reportlab/pptx/Pillow) |

200 faol o'qituvchidan real holatda bir vaqtning o'zida ~10–30 tasi generatsiya kutadi,
qolgani ro'yxat ko'radi yoki tahrir qiladi. Shuning uchun **"sekundiga nechta so'rov"**
noto'g'ri o'lcham. To'g'ri o'lchamlar:

1. Bir vaqtda nechta AI chaqiruvi **provayder kvotasiga** sig'adi
2. Nechta render **CPU yadrolariga** sig'adi
3. Nechta ulanish **Postgres'ga** sig'adi

Butun reja shu uchta sonni boshqarishga qurilgan.

---

## 2. Hozirgi holat

### 2.1 Nima allaqachon yaxshi

Bularni buzmaslik kerak:

- **Eksportlar event loop'ni bloklamaydi** — `asyncio.to_thread` bilan o'ralgan
  (`routers/materials.py:1694+`). Bu ko'p loyihada yo'q bo'lgan narsa.
- **Balans yechish atomik** — `limits.py` bitta `UPDATE ... WHERE balance >= :amt
  RETURNING` ishlatadi, read-modify-write poygasi yo'q.
- **Security header'lar to'liq** — `nosniff`, `X-Frame-Options: DENY`, qat'iy CSP,
  HSTS (localhost'dan tashqari). `/uploads` dagi saqlangan XSS yopilgan.
- **Rate limiting ikki qavat** — xotiradagi flood guard bazaga yetib bormaydi;
  o'lchangan: 120 parallel `/register/send-code` bazani qotirgan, shuning uchun
  arzon qavat oldinda turadi.
- **Refresh token rotatsiyasi** bor, bazada faqat hash saqlanadi.
- **Connection pool** to'g'ri sozlangan: `pool_timeout`, `pool_recycle`, `pool_pre_ping`.
- **Kalit rotatsiyasi yuk testi bilan asoslangan** — `ai_service.py:4060` dagi
  402 va 429 ni farqli ishlash qarori o'lchovga tayanadi.

### 2.2 Miqyoslashga to'sqinlik qiladigan narsalar

| # | Muammo | Joyi | Oqibati |
|---|---|---|---|
| B1 | **Jarayon xotirasidagi holat** — `_ai_semaphore`, `_ai_waiting`, `_exhausted_keys`, rate-limit deque'lari | `security.py:254`, `ai_service.py:4004`, `rate_limit.py` | Ikkinchi worker qo'shilsa, har biri o'z hisobini yuritadi |
| B2 | **Bitta worker majburlangan** | `start.sh`, `Dockerfile` | Gorizontal miqyoslash umuman yo'q |
| B3 | **Yuklamalar lokal diskda** | `main.py:22`, `StaticFiles` mount | Ikkinchi instansiya avatarlarni ko'rmaydi |
| B4 | **Migratsiya yo'q** | `database.py:73` `create_all` + qo'lda `ALTER` | Ikki instansiya bir vaqtda ko'tarilsa poyga; sxema o'zgarishi kuzatilmaydi |
| B5 | **AI chaqiruvi so'rov ichida, 180 s timeout** | `ai_service.py:4078` | Ulanish uzoq band; qayta urinish yo'q; server qayta ishga tushsa ish yo'qoladi |
| B6 | **Monitoring yo'q** | — | Sekinlashuvni faqat foydalanuvchi aytganda bilamiz |

**B2 haqida muhim aniqlik:** `start.sh` va `Dockerfile` bitta worker sababini
`MAX_MATERIALS_PER_DAY` hisoblagichi deb ko'rsatadi. **Bu sabab eskirgan** —
`ai_service.py:4042` dagi izoh o'zi aytadi: *"nothing reads settings.MAX_MATERIALS_PER_DAY
as an enforced limit anymore"*. Butun kodda uni o'qiydigan joy yo'q. Ya'ni o'sha
cheklovni ushlab turgan asl sabab allaqachon yo'qolgan; qolgan haqiqiy sabab — B1.

### 2.3 Ikkita aniq son

Bu ikki hisob Redis nega kerakligini boshqa har qanday dalildan yaxshiroq ko'rsatadi.

**Postgres ulanishlari:**

```
DB_POOL_SIZE=10 + DB_MAX_OVERFLOW=20  =  30 ulanish / jarayon
Postgres default max_connections      =  100

1 worker  ->  30   OK
3 worker  ->  90   chegarada
6 worker  ->  180  "too many connections"
```

**AI parallelligi:**

```
MAX_CONCURRENT_AI_CALLS = 8  / jarayon
Cerebras TPM kvotasi         = 5 kalit uchun UMUMIY (yuk testi bilan aniqlangan)

1 worker  ->  8    OK
6 worker  ->  48   429 bo'roni, muvaffaqiyat 8/10 dan 4/10 ga tushadi
```

Xulosa: **worker sonini ko'paytirishdan oldin** bu ikki chegara jarayondan tashqariga
chiqarilishi shart. Aks holda miqyoslash ishni yaxshilamaydi, yomonlashtiradi.

### 2.4 Xavfsizlik

| # | Muammo | Jiddiylik |
|---|---|---|
| X1 | `backend/.env` va `frontend/.env.local` **git'da kuzatilyapti** — AI kalitlari ×5, SMTP paroli, Postgres paroli, `SECRET_KEY` tarixda | Yuqori |
| X2 | Baza **`postgres` superuser** bilan ulanadi (`DATABASE_URL_SYNC`) | Yuqori |
| X3 | Access token **24 soat** (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`), bekor qilish mumkin emas | O'rta |
| X4 | `ADMIN_PASSWORD` doimiy ravishda env'da turadi, har boot'da o'qiladi | O'rta |
| X5 | Generatsiya kvotasi faqat bazada; Redis'siz ko'p instansiyada aylanib o'tish mumkin | O'rta |

X1 bo'yicha muhim nuqta: repo private bo'lsa ham, **kalitlarni almashtirish** tarixni
tozalashdan muhimroq. Tarix nusxalangan bo'lishi mumkin; almashtirilgan kalit esa
nusxadagi eskisini foydasiz qiladi.

---

## 3. Maqsadli arxitektura

Asosiy g'oya: **uch yo'lakka ajratish**. Har yo'lak o'z resursiga ega va biri
ikkinchisini qotirmaydi.

```
                    +-----------------+
   brauzer / APK -> |  Cloudflare     |  volumetrik himoya, TLS, CDN
                    +--------+--------+
                             |
                    +--------v--------+
                    |  nginx          |  reverse proxy, statik, upload limit
                    +--------+--------+
                             |
          +------------------+------------------+
          |                  |                  |
   +------v------+   +-------v-------+   +------v------+
   |  API xN     |   |  AI worker xM |   | Render xK   |
   |  (stateless)|   |  (navbat)     |   | (navbat)    |
   |  arzon      |   |  10-180 s     |   |  CPU        |
   +------+------+   +-------+-------+   +------+------+
          |                  |                  |
          +---------+--------+---------+--------+
                    |                  |
             +------v------+    +------v------+
             |  PostgreSQL |    |   Redis     |
             | (+pgbouncer)|    | navbat +    |
             |             |    | semafor +   |
             |             |    | rate limit  |
             +------+------+    +-------------+
                    |
             +------v------+
             | Object      |  avatarlar, yuklangan fayllar
             | storage     |  (S3-mos: MinIO yoki provayder)
             +-------------+
```

### 3.1 Nega aynan shunday

**API yo'lagi** — bu "ko'p userga chidash" degan qismning o'zi. Stateless bo'lgani
uchun nusxasini ko'paytirish arzon. 100–200 faol o'qituvchining 95% trafigi shu yerda
va u millisekundlarda tugaydi.

**AI yo'lagi navbat orqali** — bu eng muhim o'zgarish. Hozir o'qituvchi "Yaratish"
bosganda HTTP ulanishi 180 sekundgacha ochiq turadi. Navbatda esa:

```
POST /api/materials/generate  ->  202 {"job_id": "..."}   (darhol)
GET  /api/jobs/{job_id}       ->  {"status": "queued", "position": 3}
                              ->  {"status": "running"}
                              ->  {"status": "done", "material_id": "..."}
```

Bu nima beradi:

- Server qayta ishga tushsa ish **yo'qolmaydi** — navbatda qoladi
- Cho'qqida foydalanuvchi xato emas, **navbatdagi o'rnini** ko'radi
- AI parallelligi bitta joyda — worker soni bilan — boshqariladi
- Muvaffaqiyatsiz ishni qayta urinish arzon

Ilova tomonida bu katta o'zgarish emas: `generate-konspekt-stream` allaqachon bor va
`rate_limit.py` dagi `_EXEMPT_PREFIXES` progress polling uchun ochiq qoldirilgan — ya'ni
poll qilish namunasi kodda allaqachon mavjud.

**Render yo'lagi** — eksportlar `to_thread` da, lekin thread pool GIL'ni bo'lishadi va
reportlab sof Python. Alohida jarayonlarga chiqarish yagona haqiqiy yechim.

### 3.2 Komponent tanlovlari

| Komponent | Tanlov | Sabab |
|---|---|---|
| Navbat | **ARQ** | Redis ustida, sof asyncio. Celery async bilan yomon ishlaydi, bu kod esa to'liq async. ARQ kichik, o'qib chiqsa bo'ladi |
| Kesh/semafor | **Redis** | B1 dagi to'rtta holatning hammasi uchun yagona javob |
| Fayl saqlash | **S3-mos** | MinIO (o'z serveringda) yoki provayder. Kod bir xil |
| Migratsiya | **Alembic** | Allaqachon `requirements.txt` da (`alembic==1.14.0`), faqat ishlatilmayapti |
| Pool | **pgbouncer** (4-bosqichda) | 6+ jarayon bo'lganda yagona yo'l |
| Monitoring | **Sentry + `/metrics`** | Xato va sekinlashuvni foydalanuvchidan oldin ko'rish |

---

## 4. Bosqichlar

Har bosqich mustaqil qiymat beradi va alohida deploy qilinadi. Keyingisiga o'tishdan
oldin qabul mezoni bajarilishi shart.

### 0-bosqich — Xavfsizlik tarmog'i (kod o'zgarmaydi)

Hech narsani buzmasdan, ko'rish qobiliyatini beradi.

1. **Postgres backup** — kunlik `pg_dump`, tiklanishi **sinab ko'rilgan**
2. **Sentry** — backend va frontend uchun
3. **Yuk testi bazasi** — hozirgi holatni o'lchash (`scratchpad_loadtest` papkasi bor)
4. `/api/health` ga `db` va `redis` tekshiruvi qo'shish

**Qabul mezoni:** backup'dan bo'sh bazaga tiklab ko'rilgan; hozirgi cho'qqi sig'imi
raqam bilan ma'lum.

### 1-bosqich — Xavfsizlik (X1–X5)

Bu miqyoslashdan **oldin**, chunki ko'p instansiya hujum yuzasini kengaytiradi.

1. `.env` fayllarini git kuzatuvidan chiqarish, `.gitignore` ga qo'shish
2. **Hamma sirni almashtirish**: AI kalitlari ×5, SMTP app password, Postgres paroli,
   `SECRET_KEY`, Twilio/Robita, Google
3. `SECRET_KEY` almashtirish barcha JWT'ni bekor qiladi -> bir marta qayta login.
   Muqobil: eski kalitni faqat *decode* uchun N kun qabul qilish
4. Baza uchun **cheklangan rol** yaratish (superuser emas): faqat o'z sxemasiga
   `SELECT/INSERT/UPDATE/DELETE`
5. Access token **30 daqiqa** ga tushirish — refresh rotatsiyasi allaqachon bor,
   ya'ni foydalanuvchi buni sezmaydi
6. `ADMIN_PASSWORD` ni bir martalik bootstrap'ga aylantirish

**Qabul mezoni:** git'da hech qanday sir yo'q; eski kalitlar bilan API'ga kirib
bo'lmaydi; baza roli superuser emas.

### 2-bosqich — Ilovani stateless qilish

Bu bosqichdan keyin worker sonini ko'paytirish **xavfsiz** bo'ladi.

1. Redis qo'shish
2. `_ai_semaphore` -> Redis'da taqsimlangan semafor (bitta global limit)
3. `_exhausted_keys` -> Redis set, TTL bilan (kredit to'ldirilsa o'zi tiklanadi)
4. `rate_limit.py` -> ikki qavat qoladi: mahalliy deque (arzon) + Redis (aniq)
5. `uploads/` -> object storage; `StaticFiles` mount o'rniga imzolangan URL
6. **Alembic'ni yoqish**: hozirgi sxemadan boshlang'ich migratsiya (`stamp head`),
   `create_all` ni boot'dan olib tashlash, migratsiya deploy qadamiga o'tadi
7. `start.sh` va `Dockerfile` dagi eskirgan bitta-worker izohini yangilash,
   `WEB_CONCURRENCY` ni ochish
8. `DB_POOL_SIZE` ni worker soniga qarab qayta hisoblash

**Qabul mezoni:** 3 worker bilan yuk testi 1 worker'dagidan yaxshi natija beradi;
ikki instansiya bir xil avatarni ko'radi; `alembic upgrade head` sxemani yaratadi.

### 3-bosqich — Generatsiya navbati

1. ARQ qo'shish, AI worker jarayoni alohida
2. `/generate`, `/generate-all` -> `202 + job_id`
3. `GET /api/jobs/{id}` — holat, navbatdagi o'rin, natija
4. Frontend va Flutter'da poll/SSE (ikkalasida ham namuna bor)
5. Qayta urinish siyosati: 429 -> kutib qayta, 402 -> kalit almashtirib qayta,
   boshqa xato -> 2 marta
6. Ish uzilib qolsa tozalash (stuck job reaper)

**Qabul mezoni:** generatsiya paytida backend qayta ishga tushsa, ish tugaydi;
50 bir vaqtdagi generatsiya so'rovi xatosiz navbatga tushadi.

### 4-bosqich — Render navbati va sig'im

1. Eksportlar -> alohida worker pool (CPU bo'yicha o'lchangan)
2. pgbouncer (transaction pooling)
3. API instansiyalarini nginx orqasida ko'paytirish
4. `lesson_image_cache` dan tashqari, og'ir `GET` lar uchun kesh

**Qabul mezoni:** 200 bir vaqtda faol sessiya bilan p95 < 300 ms (arzon so'rovlar).

### 5-bosqich — Kuzatuv va xarajat nazorati

1. Redis'da kalit bo'yicha TPM hisobi — 429 ni oldindan ko'rish
2. Dashboard: navbat chuqurligi, AI muvaffaqiyat foizi, o'rtacha generatsiya vaqti
3. Foydalanuvchi bo'yicha xarajat hisoboti

---

## 5. Sig'im hisobi (5 000 o'qituvchi)

Boshlang'ich nuqta, yuk testidan keyin aniqlanadi:

| Resurs | Boshlang'ich | Izoh |
|---|---|---|
| API instansiya | 2 × 2 worker = 4 jarayon | Stateless, oson ko'payadi |
| DB pool | 8 + 12 = 20 / jarayon -> 80 | pgbouncer'siz `max_connections=100` ga sig'adi |
| AI worker | 2 jarayon, global semafor **10** | TPM kvotasi 8 dan yuqorida 429 bera boshlagan |
| Render worker | yadro soni − 1 | Sof CPU |
| PostgreSQL | 4 GB RAM, 2–4 vCPU | Alohida host |
| Redis | 512 MB | Navbat + hisoblagichlar |
| Object storage | 50 GB dan | Avatar + yuklamalar |

---

## 6. Ochiq qarorlar

1. **Infrastruktura** — hali tanlanmagan. Reja ataylab ko'chma: hamma komponent
   Docker Compose'da ham, alohida boshqariladigan servislarda ham ishlaydi.
   2-bosqichdan oldin tanlash kifoya.
2. **Object storage** — o'z MinIO (arzon, o'zing boqasan) yoki provayder (qimmatroq,
   backup o'zida).
3. **`SECRET_KEY` almashtirish usuli** — bir marta majburiy qayta login (oddiy),
   yoki ikki kalitli grace period (murakkabroq, sezilmaydi).
4. **Navbatga o'tish ilova versiyasini buzadi** — eski APK'lar sinxron javob kutadi.
   Yechim: `/generate` ikkala rejimni ham qo'llab-quvvatlasin, eski mijozlar uchun
   server ichida kutsin.
