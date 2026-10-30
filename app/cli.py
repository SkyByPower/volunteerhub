import os
import random
from datetime import date, timedelta

import click
from flask import current_app

from .extensions import db
from .models import Assignment, Project, Volunteer

SAMPLE_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R"
    b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 88>>stream\nBT /F1 28 Tf 120 700 Td (VolunteerHub Certificate) Tj "
    b"0 -40 Td /F1 14 Tf (Sample document) Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

VOLUNTEERS = [
    ("Айгерім Сәрсенова", "aigerim@volunteer.kz", "Алматы", "фото, SMM, ағылшын тілі"),
    ("Дамир Нұрланов", "damir@volunteer.kz", "Астана", "логистика, жүргізуші"),
    ("Мадина Ахметова", "madina@volunteer.kz", "Шымкент", "медицина, бірінші көмек"),
    ("Арман Қасымов", "arman@volunteer.kz", "Алматы", "IT, дизайн"),
    ("Анна Ким", "anna@volunteer.kz", "Қарағанды", "педагогика, ағылшын тілі"),
    ("Ерлан Төлеуов", "erlan@volunteer.kz", "Астана", "құрылыс, техника"),
    ("Жансая Бекова", "zhansaya@volunteer.kz", "Алматы", "музыка, балалармен жұмыс"),
    ("Тимур Исаев", "timur@volunteer.kz", "Павлодар", "спорт, ұйымдастыру"),
    ("Әсел Жұмабаева", "asel@volunteer.kz", "Атырау", "ветеринария, жануарлар"),
    ("Нұрсұлтан Оспанов", "nursultan@volunteer.kz", "Шымкент", "аударма, редакция"),
]

PROJECTS = [
    ("Таза Алматы: тау бөктерін тазалау", "ecology", "Алматы, Медеу",
     "Медеу мен Шымбұлақ аймағындағы соқпақтарды қоқыстан тазалау акциясы. Қолғап пен қаптар беріледі."),
    ("Балаларға кітап оқу клубы", "education", "Астана, №12 мектеп-интернат",
     "Апта сайын балаларға кітап оқып, оқу сауаттылығын дамытуға көмектесеміз."),
    ("Қарттар үйіне қамқорлық", "social", "Шымкент",
     "Қарт адамдармен уақыт өткізу, мерекелік концерт ұйымдастыру және тұрмыстық көмек."),
    ("Донорлық күн 2026", "health", "Алматы, Қан орталығы",
     "Қан тапсыру акциясын ұйымдастыру: тіркеу, ақпараттандыру және донорларды қолдау."),
    ("Иесіз жануарлар баспанасы", "animals", "Қарағанды",
     "Баспанадағы иттер мен мысықтарды серуендету, тамақтандыру және жаңа иелерін табу."),
    ("Ұлттық ою-өрнек шеберханасы", "culture", "Түркістан",
     "Жастарға қазақтың дәстүрлі қолөнерін үйрететін тегін шеберханалар сериясы."),
    ("Ағаш отырғызу марафоны", "ecology", "Астана, Жасыл белдеу",
     "Елорданың жасыл белдеуіне 5000 көшет отырғызу. Құрал-жабдық ұйымдастырушыдан."),
    ("IT-мектеп: ауыл жастарына бағдарламалау", "education", "Павлодар облысы",
     "Ауыл мектептерінің оқушыларына Python мен веб-әзірлеу негіздерін онлайн үйрету."),
    ("Азық-түлік банкі", "social", "Атырау",
     "Әлеуметтік осал отбасыларға азық-түлік себеттерін жинау және жеткізу."),
    ("Жүгіру марафоны — волонтерлік штаб", "health", "Алматы, Орталық стадион",
     "Қалалық марафонда су беру пункттері, медициналық көмек және тіркеу аймағында жұмыс."),
    ("Мұражай түні", "culture", "Астана, Ұлттық музей",
     "Мұражай түні шарасында қонақтарды қарсы алу, экскурсия жүргізуге көмектесу."),
    ("Мысықтарға арналған стерилизация күні", "animals", "Алматы",
     "Ветеринарлық клиникамен бірге тегін стерилизация акциясын ұйымдастыру."),
]


def register_cli(app):
    @app.cli.command("init-db")
    @click.option("--drop", is_flag=True, help="Drop existing tables first.")
    def init_db(drop):
        """Create all database tables."""
        if drop:
            db.drop_all()
        db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("seed")
    def seed():
        """Recreate the database with demo data and test accounts."""
        db.drop_all()
        db.create_all()
        random.seed(42)

        admin = Volunteer(full_name="Аспан Әкімші", email="admin@volunteer.kz", phone="+7 700 000 00 01",
                          city="Алматы", role="admin", skills="басқару, координация")
        admin.set_password("Admin123")
        admin.generate_token()
        db.session.add(admin)

        people = []
        for i, (name, email, city, skills) in enumerate(VOLUNTEERS):
            v = Volunteer(full_name=name, email=email, city=city, skills=skills,
                          phone=f"+7 701 555 {10 + i:02d} {20 + i:02d}",
                          bio="Жақсылық жасауды ұнатамын және жаңа жобаларға ашықпын.")
            v.set_password("Volunteer123")
            v.generate_token()
            people.append(v)
        db.session.add_all(people)

        projects = []
        today = date.today()
        for i, (title, cat, loc, desc) in enumerate(PROJECTS):
            start = today + timedelta(days=random.randint(-40, 45))
            status = "completed" if start < today - timedelta(days=20) else ("active" if start <= today else "planned")
            projects.append(Project(title=title, category=cat, location=loc, description=desc,
                                    start_date=start, end_date=start + timedelta(days=random.randint(1, 30)),
                                    capacity=random.choice([5, 8, 10, 15, 20]), status=status, creator=admin))
        db.session.add_all(projects)
        db.session.flush()

        docs = os.path.join(current_app.config["PRIVATE_UPLOAD_FOLDER"], "docs")
        os.makedirs(docs, exist_ok=True)
        with open(os.path.join(docs, "sample_certificate.pdf"), "wb") as f:
            f.write(SAMPLE_PDF)

        roles = ["Координатор", "Көмекші", "Фотограф", "Тіркеуші", "Жүргізуші", "Аудармашы"]
        for v in people:
            for p in random.sample(projects, 3):
                a = Assignment(project=p, volunteer=v, role_title=random.choice(roles), status="pending",
                               note="Бұл жобаға қатысуға қуаныштымын!")
                db.session.add(a)
                final = random.choice(["pending", "approved", "active", "completed", "completed", "rejected"])
                path = {"approved": ["approved"], "active": ["approved", "active"],
                        "completed": ["approved", "active", "completed"], "rejected": ["rejected"]}.get(final, [])
                for st in path:
                    a.change_status(st, admin)
                if final == "completed":
                    a.hours = random.randint(4, 40)
                    a.certificate_file = "docs/sample_certificate.pdf"
        db.session.commit()

        click.echo("Seeded demo data.")
        click.echo("  admin:     admin@volunteer.kz / Admin123")
        click.echo("  volunteer: aigerim@volunteer.kz / Volunteer123")
