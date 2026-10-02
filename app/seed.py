# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Product, User

DEMO_PRODUCTS = (
    ("Café especial", Decimal("38.90"), 6),
    ("Caneca térmica", Decimal("59.90"), 24),
    ("Caderno pontilhado", Decimal("32.50"), 3),
    ("Luminária de mesa", Decimal("119.00"), 12),
)


def seed() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == settings.admin_username))
        if user is None:
            db.add(
                User(
                    username=settings.admin_username,
                    email=settings.admin_email,
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                    is_active=True,
                )
            )
        existing_names = set(db.scalars(select(Product.name)))
        for name, price, quantity in DEMO_PRODUCTS:
            if name not in existing_names:
                db.add(
                    Product(
                        name=name,
                        price=price,
                        quantity_in_stock=quantity,
                    )
                )
        db.commit()


if __name__ == "__main__":
    seed()

