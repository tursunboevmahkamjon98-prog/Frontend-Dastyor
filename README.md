# Dastyor

AI orqali dars materiallari (konspekt, lektsiya, test, prezentatsiya,
amaliy topshiriq) yaratadigan platforma — o'qituvchilar uchun.

Bu repo frontend (Next.js) va backend (FastAPI) ikkalasini ham
saqlaydi. Mobil ilova (Flutter) alohida repoda.

## Tez ishga tushirish (Docker)

```bash
cp backend/.env.example backend/.env
# backend/.env ichiga haqiqiy qiymatlarni yozing: AI kalitlari,
# JWT maxfiy kaliti, admin telefon/parol, SMS provayder ma'lumotlari
# (to'liq ro'yxat va izohlar shu fayl ichida)

docker compose up -d --build
```

- Frontend: `http://localhost:8090`
- Backend: `http://localhost:8586/api/health`

`backend/.env` git'ga hech qachon qo'shilmaydi (bu repo public) —
`.env.example` faqat qaysi o'zgaruvchilar kerakligini ko'rsatadi,
qiymatlarsiz.

## Docker'siz, lokal development

**Frontend:**

```bash
npm ci
npm run dev
```

`http://localhost:3000` da ochiladi, `/api` so'rovlarini
`next.config.ts` orqali `BACKEND_ORIGIN` (standart:
`http://localhost:8009`) ga yo'naltiradi.

**Backend:**

```bash
cd backend
python -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env   # va to'ldiring
uvicorn app.main:app --reload --port 8009
```

## Production'ga chiqarish

To'liq qo'llanma — server tanlash, domen, Nginx+HTTPS, systemd
muqobili — asosiy (backend+mobil) repodagi `DEPLOY.md`da.

### Uzoq generatsiya va proxy timeout

Nginx'ning `proxy_read_timeout` qiymati sukut bo'yicha 60 sekund, va u
so'rov boshidan emas, **oxirgi kelgan baytdan** hisoblanadi. Material
generatsiyasi esa bundan uzoq davom etadi: AI chaqiruvining o'zi 180
sekundgacha, uch urinishgacha (`app/ai_service.py`), ustiga navbatda
kutish `AI_QUEUE_TIMEOUT_SECONDS` (`app/config.py`).

Shuning uchun generatsiya **oqim (SSE) orqali** yuboriladi —
`POST /api/materials/generate-all-stream`. U ishlayotgan vaqtida har 10
sekundda `: keep-alive` kadrini yuboradi, shuning uchun proxy'ning
timeout hisobi hech qachon 60 sekundga yetmaydi. Javob `X-Accel-Buffering: no`
bilan keladi — nginx uni buferlamay, darrov uzatadi.

Eski `POST /api/materials/generate-all` (oddiy JSON, oqimsiz) o'z
joyida qoldi: mobil ilova o'shandan foydalanadi. Uni to'g'ridan-to'g'ri
proxy orqasida ishlatsangiz, yuqoridagi 60 sekundlik chegara qaytadan
paydo bo'ladi.

`deploy/nginx-dastyor-timeouts.conf` — ixtiyoriy, lekin tavsiya
etiladi. Uni `/etc/nginx/conf.d/` ga ko'chirib nginx'ni qayta yuklasangiz,
oqimga tayanmaydigan uzoq so'rovlar (katta PDF eksporti, kitob yuklash)
ham himoyalanadi.
