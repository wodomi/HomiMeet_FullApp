import pytest
from app import create_app  # if you have factory, otherwise import app and configure

@pytest.fixture
def client(tmp_path, monkeypatch):
    # use sqlite for testing
    dbfile = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{dbfile}")
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{dbfile}'})
    with app.test_client() as client:
        with app.app_context():
            # initialize db
            from app import db
            db.create_all()
        yield client
