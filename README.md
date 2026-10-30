# 💜 VolunteerHub — Volunteer Management

Волонтерлік жобаларды басқару жүйесі / Система управления волонтёрскими проектами.

**Flask · Flask-SQLAlchemy · Flask-Login · Flask-WTF · Jinja2 · SQLite** — интерфейс екі тілде: **қазақша** және **орысша**, ашық/қараңғы тақырып, анимациялар.

![Home](docs/screenshots/01-home.jpg)

---

## ✨ Мүмкіндіктер / Возможности

| Талап | Іске асырылуы |
|---|---|
| Тіркелу / кіру / шығу | Flask-Login, `werkzeug` хэштелген құпия сөз, «Мені есте сақтау», open-redirect қорғанысы |
| Рөлдер | `admin` (толық басқару) және `volunteer` (жобаға өтінім, өз тағайындаулары, келісімшарт жүктеу). `@admin_required` декораторы |
| Модельдер (4 кесте) | `Volunteer`, `Project`, `Assignment` (Project ↔ Volunteer көп–көп байланысы, association object), `StatusLog` (статус тарихы) |
| CRUD | Жобалар, волонтерлер, тағайындаулар — қосу / көру / өңдеу / өшіру |
| Іздеу + сүзгі + сорттау | Жобалар (атауы/орны/сипаттама, санат, статус, 5 сорттау), волонтерлер (аты/email/қала/дағды, рөл, қала), тағайындаулар (статус, жоба) |
| Пагинация | Жобалар (6/бет), волонтерлер және тағайындаулар (10/бет), API (`page`, `per_page`) |
| Валидация | Міндетті өрістер, ұзындық, сан диапазоны (1–500, 0–1000), email, телефон regex, аты-жөні regex, құпия сөз күрделілігі, күн реті, email бірегейлігі |
| Файл жүктеу | Сурет (аватар, жоба мұқабасы) және PDF (келісімшарт, сертификат). `secure_filename` + UUID префикс, кеңейтім **және** файл қолтаңбасы (magic bytes) тексеріледі, 5 МБ шектеу. PDF файлдар `instance/` ішінде жабық сақталып, тек иесі/әкімшіге беріледі |
| Қате беттері | 403, 404, 413, 500 үшін custom беттер (API үшін JSON) |
| API | 12 endpoint: GET / POST / PUT / DELETE, токен арқылы аутентификация |
| Қауіпсіздік | CSRF (Flask-WTF), Jinja autoescape, ORM (SQL injection жоқ), сорттау whitelist, `.env` құпиялары |
| UI | Glassmorphism дизайн, анимациялық фон, scroll-reveal, санауыш анимациясы, ripple батырмалар, toast flash-хабарламалар, растау модалы, 3D tilt карточкалар |
| i18n | ҚАЗ / РУС ауыстырғыш (`app/i18n.py`) — барлық мәтіндер, форма қателері, flash-хабарламалар аударылған |
| Тесттер | `pytest` — 11 тест (auth, рөлдер, CRUD, іздеу, жүктеу, API) |

## 📁 Құрылым / Структура

```
├── app/
│   ├── __init__.py          # create_app() фабрикасы
│   ├── extensions.py        # db, login_manager, csrf, migrate
│   ├── models.py            # Volunteer, Project, Assignment, StatusLog
│   ├── forms.py             # WTForms + валидация
│   ├── i18n.py              # қазақша / орысша аудармалар
│   ├── utils.py             # admin_required, файл жүктеу, қауіпсіз redirect
│   ├── errors.py            # 403/404/413/500 өңдеушілері
│   ├── cli.py               # flask init-db / flask seed
│   ├── routes/              # Blueprints
│   │   ├── main.py          #   басты бет, dashboard
│   │   ├── auth.py          #   тіркелу, кіру, профиль
│   │   ├── projects.py      #   жобалар CRUD + өтінім
│   │   ├── volunteers.py    #   волонтерлер CRUD (admin)
│   │   ├── assignments.py   #   тағайындау, статус, PDF
│   │   └── api.py           #   REST API
│   ├── templates/           # Jinja2 шаблондары
│   └── static/              # css, js, uploads (суреттер)
├── tests/test_app.py
├── docs/                    # скриншоттар + Postman коллекциясы
├── config.py
├── run.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## 🚀 Орнату және іске қосу / Установка и запуск

```bash
git clone <repo-url>
cd volunteerhub
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```
macOS / Linux:
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
cp .env.example .env        # SECRET_KEY мәнін өзгертіңіз
```

### Дерекқорды инициализациялау / Инициализация БД

Демо деректермен (ұсынылады):
```bash
flask --app run.py seed
```

Тек бос кестелер:
```bash
flask --app run.py init-db
```

Flask-Migrate арқылы миграция (қаласаңыз):
```bash
flask --app run.py db init
flask --app run.py db migrate -m "initial"
flask --app run.py db upgrade
```

### Іске қосу / Запуск
```bash
flask --app run.py run
```
Браузерде ашыңыз: <http://127.0.0.1:5000>

PostgreSQL қолдану үшін `.env` ішінде: `DATABASE_URL=postgresql://user:pass@localhost/volunteer` (және `pip install psycopg2-binary`).

## 🔑 Тест аккаунттар / Тестовые аккаунты

| Рөл | Email | Құпия сөз |
|---|---|---|
| Әкімші / Администратор | `admin@volunteer.kz` | `Admin123` |
| Волонтер / Волонтёр | `aigerim@volunteer.kz` | `Volunteer123` |

Басқа волонтерлер: `damir@`, `madina@`, `arman@`, `anna@` … `@volunteer.kz` — бәрінің құпия сөзі `Volunteer123`.

## 🔌 API

Аутентификация: `X-API-Key: <token>` тақырыбы (немесе `Authorization: Bearer <token>`). Токенді `POST /api/auth/token` арқылы немесе профиль бетінен алыңыз.

| Әдіс | Endpoint | Рұқсат | Сипаттама |
|---|---|---|---|
| POST | `/api/auth/token` | — | email + құпия сөз → токен |
| GET | `/api/stats` | — | статистика |
| GET | `/api/projects?q=&category=&status=&page=&per_page=` | — | жобалар тізімі (іздеу, сүзгі, пагинация) |
| GET | `/api/projects/<id>` | — | жоба + тағайындаулар |
| POST | `/api/projects` | admin | жоба құру (валидация → 422) |
| PUT | `/api/projects/<id>` | admin | жобаны жаңарту |
| DELETE | `/api/projects/<id>` | admin | жобаны өшіру |
| GET | `/api/assignments?status=&project_id=` | token | admin — барлығы, volunteer — өзінікі |
| POST | `/api/assignments` | admin | волонтерді жобаға тағайындау (қайталанса 409) |
| PUT | `/api/assignments/<id>` | admin | статус / сағат / міндет өзгерту (тарих жазылады) |
| DELETE | `/api/assignments/<id>` | admin | тағайындауды өшіру |
| GET | `/api/volunteers?q=` | admin | волонтерлер тізімі |

Мысал:
```bash
curl -X POST http://127.0.0.1:5000/api/auth/token -H "Content-Type: application/json" -d "{\"email\":\"admin@volunteer.kz\",\"password\":\"Admin123\"}"
```

**Postman:** `docs/VolunteerHub.postman_collection.json` файлын импорттаңыз → алдымен «Get token (admin)» сұранысын жіберіңіз (токен автоматты сақталады).

## 🧪 Тесттер
```bash
pytest -q
```

## 🎬 Демо сценарий / Демо-сценарий

1. **Басты бет** — анимациялық статистика, соңғы жобалар. Жоғарғы оң жақта ҚАЗ/РУС және тақырыпты ауыстырыңыз.
2. **Тіркелу** — қате деректер енгізіп валидацияны көрсетіңіз (қысқа аты, қате email/телефон, сәйкес емес құпия сөздер).
3. **Волонтер ретінде кіру** (`aigerim@volunteer.kz`) → *Жобалар* → іздеу, санат чиптері, статус сүзгісі, сорттау, беттеу.
4. Жобаны ашып → **«Қатысуға өтінім беру»** → *Менің қатысуым* бетінде статус «Күтуде».
5. Тағайындауды ашып → **келісімшарт PDF жүктеу** (жалған `.pdf` файлы қабылданбайды).
6. **Шығып, әкімші ретінде кіру** (`admin@volunteer.kz`) → *Басқару панелі*: күтудегі өтінімдерді ✓/✕ батырмаларымен бекіту.
7. Тағайындау бетінде статусты *Белсенді → Аяқталған* етіп ауыстырыңыз — **статус тарихы** уақыт сызығында көрінеді; сертификат PDF жүктеңіз.
8. **Жоба CRUD**: жаңа жоба + мұқаба суреті → өңдеу → өшіру (растау модалы).
9. **Волонтерлер** бетінде іздеу/сүзгі, волонтерді өңдеу.
10. **API**: Postman коллекциясын іске қосыңыз; `/nope` арқылы 404 бетін көрсетіңіз.

## 🖼 Скриншоттар / Скриншоты

| | |
|---|---|
| ![Басты бет](docs/screenshots/01-home.jpg) | ![Әкімші панелі](docs/screenshots/02-admin-dashboard.jpg) |
| Басты бет (РУС, қараңғы тақырып) | Әкімші панелі |
| ![Жобалар](docs/screenshots/03-projects.jpg) | ![Тағайындаулар](docs/screenshots/04-assignments.jpg) |
| Жобалар тізімі | Тағайындаулар: сүзгі, чиптер, кесте |
| ![Тағайындау](docs/screenshots/05-assignment-detail-kk.jpg) | ![Валидация](docs/screenshots/06-validation-light.jpg) |
| Тағайындау беті (ҚАЗ): статус, PDF | Форма валидациясы (ашық тақырып) |
