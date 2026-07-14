"""Run with: python -m app.seed
Populates a handful of demo HCPs so search_or_create_hcp has real matches
to demo in your walkthrough video."""
from .database import SessionLocal, Base, engine
from . import models

Base.metadata.create_all(bind=engine)

DEMO_HCPS = [
    {"name": "Dr. Ananya Sharma", "specialty": "Oncology", "hospital": "Apollo Hospitals"},
    {"name": "Dr. Rohan Smith", "specialty": "Cardiology", "hospital": "Fortis Hospital"},
    {"name": "Dr. Meera Iyer", "specialty": "Endocrinology", "hospital": "Manipal Hospital"},
]


def run():
    db = SessionLocal()
    try:
        for hcp in DEMO_HCPS:
            exists = db.query(models.HCP).filter(models.HCP.name == hcp["name"]).first()
            if not exists:
                db.add(models.HCP(**hcp))
        db.commit()
        print(f"Seeded {len(DEMO_HCPS)} demo HCPs (skipping any that already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
