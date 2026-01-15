from sqlmodel import Session, SQLModel, create_engine
from app.services.auth import AuthService
from app.models.user import User

# Setup in-memory DB
engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(engine)

def test_registration():
    with Session(engine) as session:
        service = AuthService(session)
        print("Attempting registration...")
        try:
            user = service.register_user("debug@test.com", "password", "1234567890")
            print(f"Success! User created: {user.email}")
        except Exception as e:
            print("CRITICAL ERROR DURING REGIISTRATION:")
            print(e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_registration()
