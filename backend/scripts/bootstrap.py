from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.bootstrap_service import bootstrap_initial_data


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_initial_data(db)
        print('bootstrap done')
    finally:
        db.close()


if __name__ == '__main__':
    main()
