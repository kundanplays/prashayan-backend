from sqlmodel import Session, select
from app.db.session import engine, create_db_and_tables
from app.models.product import Product

def seed_products():
    print("Creating database and tables...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # Check if products already exist to avoid duplicates
        existing_products = session.exec(select(Product)).all()
        if existing_products:
            print(f"Database already contains {len(existing_products)} products. Skipping seed.")
            return

        print("Seeding initial products...")
        products = [
            Product(
                name="Pure Himalayan Shilajit",
                slug="shilajit-resin",
                description="Original, high-potency Shilajit resin sourced from the highest altitudes of the Himalayas. Boosts energy and vitality.",
                price=1499.00,
                stock_quantity=100,
                image_url="/images/shilajit.webp"
            ),
            Product(
                name="Shilajit Gold Plus",
                slug="shilajit-gold",
                description="A premium blend of Shilajit and Swarna Bhasma (Gold Ash) for enhanced vigor, immunity, and anti-aging benefits.",
                price=2499.00,
                stock_quantity=50,
                image_url="/images/shilajit-gold.webp"
            ),
            Product(
                name="Ashwagandha Vitality",
                slug="ashwagandha-vitality",
                description="Organic Ashwagandha root extract to reduce stress, improve sleep, and increase muscle strength.",
                price=899.00,
                stock_quantity=200,
                image_url="/images/ashwagandha.webp"
            ),
            Product(
                name="Triphala Pure Detox",
                slug="triphala-detox",
                description="A classic Ayurvedic herbal blend for digestive health, detoxification, and rejuvenation.",
                price=499.00,
                stock_quantity=150,
                image_url="/images/triphala.webp"
            ),
            Product(
                name="Kesar Radiance Elixir",
                slug="kesar-elixir",
                description="Rare Kashmiri Saffron extract infused with essential oils for glowing skin and mental clarity.",
                price=3999.00,
                stock_quantity=30,
                image_url="/images/kesar.webp"
            )
        ]

        for product in products:
            session.add(product)
        
        session.commit()
        print("Successfully seeded 5 products!")

if __name__ == "__main__":
    seed_products()
