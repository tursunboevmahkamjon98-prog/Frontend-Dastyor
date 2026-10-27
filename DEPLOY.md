# Dastyor'ни серверга кўчириш

Ҳозир лойиҳа ноутбукда ишлайди ва Cloudflare tunnel орқали интернетга
чиқарилган. Бу вақтинчалик: ноутбук ўчса — сайт ҳам, backend ҳам ўчади,
tunnel қайта ишга тушганда манзил ўзгаради.

Бу ҳужжат — доимий серверга кўчириш учун. Ҳамма нарса тайёр, сизга
фақат сервер ва домен керак.

---

## 1. Нима керак

| Нима | Изоҳ |
|---|---|
| VPS | 2 ГБ RAM, 2 ядро, 20 ГБ диск — етарли. Ubuntu 22.04 ёки 24.04 |
| Домен | `rahnamo.tj` |
| PostgreSQL | ўша серверда ёки алоҳида |

AI калитлари, SMS (Robita) ва бошқа махфий маълумотлар `backend/.env`
файлида — бу репозиторий **хусусий** (private) бўлгани учун у git билан
бирга келади (қара `.gitignore`даги изоҳ). `git clone` қилинган
серверда бошқа ҳеч нарса кўчиришнинг ҳожати йўқ.

---

## 2. Docker орқали кўчириш (тавсия этилади — энг тез йўл)

Битта буйруқ — Postgres, backend ва frontend учтаси биргаликда:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker

cd /opt
sudo git clone <repo> dastyor && cd dastyor
sudo chown -R $USER:$USER /opt/dastyor

docker compose up -d --build
```

Шу билан тамом — `docker-compose.yml` учта хизматни ўзи йиғади ва
уланади:

| Хизмат | Порт (host) | Изоҳ |
|---|---|---|
| `frontend` | `8090` | Next.js, production build |
| `backend` | `8586` | FastAPI, битта worker (сабаби пастда) |
| `db` | — (ташқарига очилмайди) | Postgres 16, `postgres_data` volume'да сақланади |

Текшириш:

```bash
docker compose ps                          # учтаси ҳам "healthy" бўлиши керак
curl -s http://localhost:8586/api/health   # {"status":"ok",...}
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8090/   # 200
```

Кейинги қадамлар (6-бўлимдаги Nginx+HTTPS) **ўзгармайди** — фақат
`proxy_pass` манзилларини `127.0.0.1:8090` (сайт) ва `127.0.0.1:8586`
(API) га қаратинг, systemd port'лари (`3000`/`8002`) ўрнига.

> **Эслатма**: `docker-compose.yml`даги `db` хизмати ФАҚАТ биринчи
> ишга тушишда `postgres_data` volume'ни яратади. Агар аллақачон
> алоҳида (масалан, бошқа серверда ёки managed) Postgres'ингиз бўлса —
> `db` хизматини `docker-compose.yml`дан ўчиринг ва
> `backend/.env`даги `DATABASE_URL`ни ўша базага қаратинг (`docker
> compose`даги `environment:` бўлими уни `db` хизматига қаратиб
> қўяди — шуни ҳам ўчириш керак бўлади).
>
> Янгилашда: `git pull && docker compose up -d --build` — эски
> image'лар ўзи алмаштирилади, volume'лар (база, юкланган файллар)
> тегилмайди.

Docker'сиз, systemd орқали қўлда ўрнатишни хоҳласангиз — қуйидаги
3–5-бўлимлар шуни тасвирлайди (иккаласи ҳам ишлайди, биттасини
танланг).

---

## 3. Серверни тайёрлаш (Docker'сиз йўл)

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv \
    postgresql nginx git curl \
    libreoffice-impress fonts-dejavu-core fonts-liberation
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

> Охирги учтаси **шарт** — уларсиз лойиҳа ишлайди, лекин нотўғри
> ишлайди, ва буни ҳеч ким сезмайди:
>
> | Пакет | Йўқ бўлса нима бўлади |
> |---|---|
> | `libreoffice-impress` | Презентация кўриниши. Код `soffice`ни топа олмай, эски A4 PDF'га тушиб кетади — **хатолик чиқмайди**, ўқитувчи шунчаки ўз слайдлари ўрнига бошқа нарсани кўради (`app/pptx_pdf.py`) |
> | `fonts-dejavu-core` | Ҳамма PDF бўш квадратчалар бўлиб чиқади. `export_builder._register_unicode_font` Linux'да `DejaVuSans.ttf`ни аниқ йўл бўйича излайди, бошқа захира йўқ |
> | `fonts-liberation` | LibreOffice Arial ўрнига бошқа шрифт қўяди, слайдлардаги сатрлар сурилиб кетади |
>
> Айнан DejaVu кераклиги сабабли: тожик тилида **ғ қ ҳ ҷ ӣ ӯ** ҳарфлари
> бор, уларни енгил базавий шрифтлар чизмайди.

Кўчиргандан кейин текшириб кўринг:

```bash
which soffice || which libreoffice     # йўл чиқиши керак
fc-list | grep -i dejavu               # камида битта қатор
```

Базани яратиш:

```bash
sudo -u postgres psql -c "CREATE DATABASE dastyor_db;"
sudo -u postgres psql -c "CREATE USER dastyor WITH PASSWORD 'КУЧЛИ_ПАРОЛ';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dastyor_db TO dastyor;"
```

---

## 4. Лойиҳани кўчириш

```bash
cd /opt
sudo git clone <repo> dastyor && cd dastyor
sudo chown -R $USER:$USER /opt/dastyor
```

`.env` файлини ноутбукдан кўчиринг ва ичидагиларни серверга мослаштиринг:

```
DATABASE_URL=postgresql+asyncpg://dastyor:КУЧЛИ_ПАРОЛ@localhost:5432/dastyor_db
CORS_ORIGINS=https://rahnamo.tj
```

Backend:

```bash
cd /opt/dastyor/backend
python3.12 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

Сайт:

```bash
cd /opt/dastyor/frontend
npm ci
NEXT_PUBLIC_API_URL=https://rahnamo.tj/api npm run build
```

> `NEXT_PUBLIC_*` **йиғиш пайтида** файлларга ёзилади. Манзил ўзгарса,
> сайтни қайта йиғиш керак — қайта ишга тушириш етарли эмас.

---

## 5. Хизматлар (systemd)

`/etc/systemd/system/dastyor-api.service`:

```ini
[Unit]
Description=Dastyor API
After=network.target postgresql.service

[Service]
WorkingDirectory=/opt/dastyor/backend
ExecStart=/opt/dastyor/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8002 --workers 1
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/dastyor-web.service`:

```ini
[Unit]
Description=Dastyor web
After=network.target

[Service]
WorkingDirectory=/opt/dastyor/frontend
Environment=NEXT_PUBLIC_API_URL=https://rahnamo.tj/api
ExecStart=/usr/bin/npx next start -p 3000
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dastyor-api dastyor-web
```

> `--workers 1` — **атайлаб**. Бу ерда ҳамма чеклов битта процесснинг
> хотирасида саналади: AI'нинг бир вақтдаги чақирувлари
> (`security.py`, `MAX_CONCURRENT_AI_CALLS=8`), флуд қўриқчиси
> (`rate_limit.py`) ва Wikimedia'нинг circuit breaker'и
> (`image_builder.py`). Уч worker уларни бўлишмайди — ҳар бир чеклов
> жимгина 3 баробар бўшашади. Биринчи бўлиб AI провайдернинг дақиқалик
> квотаси ёрилади, ва у **ҳамманинг** генерациясини 429 қилиб қайтаради,
> фақат ортиқчасини эмас. 3 та worker `start.sh`га ҳам зид эди.
>
> Кўпроқ юкга чидаш керак бўлса — аввал шу ҳисоблагичларни Redis'га
> кўчириш керак, кейин worker сонини ошириш мумкин.

---

## 6. Nginx ва HTTPS

> Docker йўли учун: пастдаги `proxy_pass` манзилларида
> `127.0.0.1:3000` ўрнига `127.0.0.1:8090`, `127.0.0.1:8002` ўрнига
> `127.0.0.1:8586` ёзинг — қолгани бир хил.

`/etc/nginx/sites-available/dastyor`:

```nginx
server {
    server_name rahnamo.tj;

    # Сайт
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    # API — /api билан бошланадиган ҳамма нарса backend'га
    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        client_max_body_size 20M;      # китоб юклаш учун
    }

    # Расмлар
    location /uploads/ {
        proxy_pass http://127.0.0.1:8002;
    }
}
```

### Timeout — **шарт**, акс ҳолда презентация ишламайди

nginx'нинг `proxy_read_timeout` қиймати ўзгартирилмаса **60 сония**.
Презентация эса `POST /api/materials/generate` орқали яратилади ва
тайёр бўлгунича **битта ҳам байт қайтармайди** — AI чақирувининг ўзи
180 сониягача (`ai_service.py`), навбатда кутиш яна 120 сониягача
(`config.py`). 60 сониядан ошганда nginx backend'ни ташлаб, ўзининг
504 саҳифасини қайтаради. Унда JSON `detail` йўқ, шунинг учун frontend
(`lib/api.ts`) охирги чора сифатида "**Ошибка сервера**" деб кўрсатади —
бу хабарни backend ҳеч қачон юбормайди. Локалда nginx йўқ, шунинг учун
у ерда ҳаммаси ишлайверади.

Конспект шу пайтда ҳам ишлаган, чунки у бошқа йўлдан —
`/generate-konspekt-stream` (SSE) — кетади ва байтлар дарҳол оқа
бошлайди, timeout умуман ишламайди. Презентацияда бундай stream йўқ.

Тузатиш (`certbot` тегмайдиган жойга қўйилади):

```bash
sudo cp /opt/dastyor/deploy/nginx-dastyor-timeouts.conf \
        /etc/nginx/conf.d/dastyor-timeouts.conf
sudo nginx -t && sudo systemctl reload nginx
```

> `X-Forwarded-For` **шарт**: SMS ва флуд лимитлари шу сарлавҳадан
> фойдаланувчининг ҳақиқий манзилини олади (`app/rate_limit.py`,
> `routers/auth.py:_client_ip`). Усиз ҳамма фойдаланувчи битта манзил
> кўринади ва биринчи банд бўлган дақиқада ҳаммаси блокланади.

```bash
sudo ln -s /etc/nginx/sites-available/dastyor /etc/nginx/sites-enabled/
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d rahnamo.tj      # HTTPS'ни ўзи созлайди
```

Шундан кейин сайт ва backend **битта доменда** бўлади — CORS муаммоси
умуман йўқолади.

---

## 7. Заҳира нусхалар

```bash
# ҳар куни соат 3:00 да
sudo crontab -e
0 3 * * * cd /opt/dastyor/backend && ./venv/bin/python backup_db.py --keep 30
```

> Docker йўли учун: база `db` хизмати ичида, `backend` контейнерида
> эмас — заҳира ҳам шундан олинади:
> ```bash
> 0 3 * * * docker compose -f /opt/dastyor/docker-compose.yml exec -T db \
>     pg_dump -U postgres dastyor_db | gzip > /opt/backups/dastyor_$(date +\%Y\%m\%d).sql.gz
> ```

Заҳираларни серверда қолдирманг — ҳафтада бир марта бошқа жойга
кўчиринг. Сервер йўқолса, заҳира ҳам у билан кетади.

---

## 8. Мобил илова

Сервер тайёр бўлгач, APK'ни доимий манзил билан қайта йиғинг:

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://rahnamo.tj
```

Имзо калити ҳақида — `android/key.properties.example`.

### Янги версия чиқариш

APK Play Market орқали тарқатилмайди ва илова ичида янгиланишни
текширадиган механизм **йўқ** (у қўшилган эди, кейин олиб ташланди).
Демак янги версия чиққанини фойдаланувчиларга **ўзингиз** хабар
қилишингиз керак:

1. `flutter build apk --release --dart-define=API_BASE_URL=https://rahnamo.tj`
2. `cp build/app/outputs/flutter-apk/app-release.apk frontend/public/dastyor.apk`
   (очиқ репода ҳам — `public/dastyor.apk`), кейин commit + push + серверда
   `git pull && docker compose up -d --build`
3. `/admin` дан ҳамма ўқитувчига СМС: янги версия чиқди, `rahnamo.tj/dastyor.apk`

> `pubspec.yaml`даги `version:`ни ҳар сафар оширинг. Акс ҳолда
> телефондаги "Иловалар" рўйхатида ҳамма APK бир хил версия бўлиб
> кўринади ва қайси бири турганини аниқлаб бўлмайди.

Сайтда Android'дан кирганларга кичик хабар кўрсатилади
(`src/components/AppUpdateBanner.tsx`) — у СМС'нинг ўрнини босмайди,
фақат сайтга кирганлар кўради.

`GET /api/app/version` endpoint'и жойида қолди, лекин ҳозир уни ҳеч ким
ўқимайди. Келажакда илова ичидаги текширув қайта керак бўлса, тайёр
турибди (`APP_LATEST_BUILD` ва қўшнилари — `backend/.env`да).

---

## 9. Кўчиргандан кейин текширинг

- [ ] `https://rahnamo.tj` очилади, кириш ишлайди
- [ ] янги материал яратилади (AI калитлари серверда ишлаяпти)
- [ ] SMS келади (Robita серверда ишлаяпти)
- [ ] PDF юкланади ва расмлар кўринади (`/uploads/`)
- [ ] PDF ичида ҳарфлар кўринади, квадратча эмас — айниқса тожикча
      **ғ қ ҳ ҷ ӣ ӯ** (шрифтлар ўрнатилганини шу кўрсатади)
- [ ] презентация кўриниши ҳақиқий слайдларни кўрсатади, A4 варақни эмас
      (LibreOffice ишлаяпти)
- [ ] `.env` даги `CORS_ORIGINS` фақат ҳақиқий доменни ўз ичига олади —
      эски `trycloudflare.com` манзиллари ўчирилган
- [ ] `.env` дан `DOCS_ENABLED` қатори **ўчирилган** (ёки `false`).
      Бу репозиторийда `.env` git билан бирга келади, ундаги
      `DOCS_ENABLED=true` эса фақат ноутбукдаги иш учун. Сервер уни
      мерос қилиб олса, `/docs` очиқ қолади ва ҳамма endpoint,
      admin'никилари ҳам, рўйхат бўлиб кўринади:
      `curl -s -o /dev/null -w '%{http_code}' https://rahnamo.tj/docs`
      → **404** бўлиши керак
- [ ] `backup_db.py` ишлайди (ёки Docker йўлида — `pg_dump` cron'и)
- [ ] Docker йўли: `docker compose ps` барча уч хизматни ҳам
      "healthy" деб кўрсатади
- [ ] ноутбукдаги tunnel ва dev серверлар **ўчирилган**
