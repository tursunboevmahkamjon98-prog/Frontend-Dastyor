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

### Nginx timeout — o'tkazib yubormang

Nginx orqasiga qo'yayotgan bo'lsangiz, `deploy/nginx-dastyor-timeouts.conf`
ni `/etc/nginx/conf.d/` ga ko'chiring va nginx'ni qayta yuklang.

Nginx'ning `proxy_read_timeout` qiymati sukut bo'yicha 60 sekund.
Prezentatsiya esa `POST /api/materials/generate` orqali yaratiladi va
tayyor bo'lguncha bitta ham bayt qaytarmaydi — faqat AI chaqiruvining
o'zi 180 sekundgacha (`app/ai_service.py`), ustiga navbatda kutish
`AI_QUEUE_TIMEOUT_SECONDS` (`app/config.py`). 60 sekunddan oshganda
nginx backend'ni tashlab, JSON `detail`i yo'q 504 sahifasini qaytaradi
va foydalanuvchi "Ошибка сервера" degan, backend hech qachon
yubormaydigan xabarni ko'radi. Lokalda nginx bo'lmagani uchun bu faqat
production'da chiqadi.
