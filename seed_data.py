from sqlmodel import Session, select
from app.db.session import engine, create_db_and_tables
from app.models.product import Product
from app.models.user import User
from app.core.security import get_password_hash

def seed_products():
    print("Creating database and tables...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # Clear existing products for a fresh seed
        print("Clearing existing products...")
        # session.exec(select(Product)).all() # Just to be safe with any relation issues, but simple delete is better
        from sqlmodel import delete
        session.exec(delete(Product))
        session.commit()

        print("Seeding initial products...")
        products = [
            Product(
                name="Pure Himalayan Shilajit",
                slug="shilajit-resin",
                description="Original, high-potency Shilajit resin sourced from the highest altitudes of the Himalayas. Boosts energy and vitality.",
                mrp=1999.00,
                selling_price=1499.00,
                stock_quantity=100,
                image_urls=["products/shilajit.webp", "products/shilajit.png"],
                thumbnail_url="products/shilajit.webp",
                ingredients="Pure Himalayan Shilajit Resin",
                benefits="Boosts energy, enhances stamina, supports immune system, improves cognitive function",
                how_to_use="Dissolve a pea-sized portion in warm water or milk. Consume once daily, preferably in the morning.",
                is_active=True
            ),
            Product(
                name="Shilajit Gold Plus",
                slug="shilajit-gold",
                description="A premium blend of Shilajit and Swarna Bhasma (Gold Ash) for enhanced vigor, immunity, and anti-aging benefits.",
                mrp=2999.00,
                selling_price=2499.00,
                stock_quantity=50,
                image_urls=["products/shilajit-gold.webp"],
                thumbnail_url="products/shilajit-gold.webp",
                ingredients="Shilajit Extract, Swarna Bhasma (Gold Ash), Ashwagandha",
                benefits="Enhanced vitality, anti-aging properties, improved immunity, better cognitive function",
                how_to_use="Take 1-2 capsules daily with warm milk or water after meals.",
                is_active=True
            ),
            Product(
                name="Ashwagandha Vitality",
                slug="ashwagandha-vitality",
                description="Organic Ashwagandha root extract to reduce stress, improve sleep, and increase muscle strength.",
                mrp=1199.00,
                selling_price=899.00,
                stock_quantity=200,
                image_urls=["products/ashwagandha.webp"],
                thumbnail_url="products/ashwagandha.webp",
                ingredients="Organic Ashwagandha Root Extract (Withania somnifera)",
                benefits="Reduces stress and anxiety, improves sleep quality, increases muscle strength, balances hormones",
                how_to_use="Take 1-2 capsules daily with water, preferably before bedtime.",
                is_active=True
            ),
            Product(
                name="Triphala Pure Detox",
                slug="triphala-detox",
                description="A classic Ayurvedic herbal blend for digestive health, detoxification, and rejuvenation.",
                mrp=699.00,
                selling_price=499.00,
                stock_quantity=150,
                image_urls=["products/triphala.webp"],
                thumbnail_url="products/triphala.webp",
                ingredients="Amalaki (Emblica officinalis), Bibhitaki (Terminalia bellirica), Haritaki (Terminalia chebula)",
                benefits="Improves digestion, natural detoxification, supports weight management, enhances nutrient absorption",
                how_to_use="Mix 1 teaspoon with warm water and consume before bedtime or early morning on an empty stomach.",
                is_active=True
            ),
            Product(
                name="Kesar Radiance Elixir",
                slug="kesar-elixir",
                description="Rare Kashmiri Saffron extract infused with essential oils for glowing skin and mental clarity.",
                mrp=4999.00,
                selling_price=3999.00,
                stock_quantity=30,
                image_urls=["products/kesar.webp"],
                thumbnail_url="products/kesar.webp",
                ingredients="Kashmiri Saffron (Crocus sativus), Almond Oil, Rose Water, Sandalwood Extract",
                benefits="Promotes glowing skin, improves complexion, enhances mental clarity, anti-aging properties",
                how_to_use="Apply a few drops to face and neck, or add to warm milk and consume daily.",
                is_active=True
            ),
            Product(
                name="Organic Tulsi Drops",
                slug="tulsi-drops",
                description="Concentrated Holy Basil extract for respiratory health and stress management.",
                mrp=499.00,
                selling_price=349.00,
                stock_quantity=300,
                image_urls=["products/tulsi.png"],
                thumbnail_url="products/tulsi.png",
                ingredients="Concentrated Tulsi Extract",
                benefits="Respiratory support, anti-stress, immune booster",
                how_to_use="Add 2-3 drops to water or tea, twice daily.",
                is_active=True
            ),
            Product(
                name="Neem Purifying Capsules",
                slug="neem-capsules",
                description="Natural blood purifier and skin health support using organic Neem leaf extract.",
                mrp=599.00,
                selling_price=449.00,
                stock_quantity=200,
                image_urls=["products/neem.png"],
                thumbnail_url="products/neem.png",
                ingredients="Organic Neem Leaf Extract",
                benefits="Blood purification, skin health, anti-fungal properties",
                how_to_use="Take 1 capsule twice daily with water after meals.",
                is_active=True
            ),
            Product(
                name="Turmeric Curcumin Plus",
                slug="turmeric-capsules",
                description="High-absorption turmeric complex with black pepper for joint health and inflammation support.",
                mrp=899.00,
                selling_price=699.00,
                stock_quantity=100,
                image_urls=["products/turmeric.png"],
                thumbnail_url="products/turmeric.png",
                ingredients="Turmeric Extract (95% Curcuminoids), Black Pepper Extract",
                benefits="Anti-inflammatory, joint support, digestive health",
                how_to_use="Take 1-2 capsules daily with food.",
                is_active=True
            )
        ]

        for product in products:
            session.add(product)
        
        session.commit()
        print(f"Successfully seeded {len(products)} products!")

if __name__ == "__main__":
    seed_products()
