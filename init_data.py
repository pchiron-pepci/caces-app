from app.database import SessionLocal
from app.models.categorie import Famille, Categorie
from app.models.testeur import Testeur
from app.models.habilitation_testeur import HabilitationTesteur
from datetime import date

def init_data():
    db = SessionLocal()
    try:
        if db.query(Famille).count() > 0:
            print("Donnees deja initialisees !")
            return

        print("Initialisation des donnees CACES...")

        # === FAMILLES ===
        r482 = Famille(code="R482", libelle="Engins de chantier", validite_ans=10)
        r483 = Famille(code="R483", libelle="Grues a tour", validite_ans=5)
        r484 = Famille(code="R484", libelle="Ponts roulants et portiques", validite_ans=5)
        r485 = Famille(code="R485", libelle="Gerbeurs a conducteur accompagnant", validite_ans=5)
        r486 = Famille(code="R486", libelle="Plates-formes elevatrices mobiles de personnel", validite_ans=5)
        r487 = Famille(code="R487", libelle="Grues mobiles", validite_ans=5)
        r489 = Famille(code="R489", libelle="Chariots de manutention automoteurs a conducteur porte", validite_ans=5)
        r490 = Famille(code="R490", libelle="Grues de chargement", validite_ans=5)
        db.add_all([r482, r483, r484, r485, r486, r487, r489, r490])
        db.flush()

        # === CATEGORIES ===
        categories = [
            # R482 - Engins de chantier
            Categorie(famille_id=r482.id, code="A",       libelle="Engins compacts",                              ut_pratique=1.5,  pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r482.id, code="B1",      libelle="Engins extraction deplacement sequentiel",     ut_pratique=1.0,  pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r482.id, code="B2",      libelle="Engins extraction rotatifs",                   ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r482.id, code="B3",      libelle="Engins extraction a chenilles",                ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r482.id, code="C1",      libelle="Engins chargement deplacement alternatif",     ut_pratique=1.0,  pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r482.id, code="C2",      libelle="Engins chargement rotatifs",                   ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r482.id, code="C3",      libelle="Engins chargement a chenilles",                ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r482.id, code="D",       libelle="Engins de compactage",                        ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r482.id, code="E",       libelle="Engins de finissage",                         ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r482.id, code="F",       libelle="Chariots manutention tout terrain",            ut_pratique=1.0,  pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r482.id, code="G",       libelle="Engins de forage et fondations",               ut_pratique=1.2,  pepci_habilite=False),
            Categorie(famille_id=r482.id, code="OPT-TEL", libelle="Option Telecommande",                          ut_pratique=0.5,  pepci_habilite=True,  est_option=True),
            Categorie(famille_id=r482.id, code="OPT-PE",  libelle="Option Porte-Engins",                          ut_pratique=0.5,  pepci_habilite=True,  est_option=True),

            # R483 - Grues a tour
            Categorie(famille_id=r483.id, code="1",       libelle="Grues a tour a montage automatise",            ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r483.id, code="2",       libelle="Grues a tour a montage non automatise",        ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r483.id, code="3",       libelle="Grues a tour a fleche relevable",              ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r483.id, code="4",       libelle="Grues a tour sur porteur",                     ut_pratique=1.0,  pepci_habilite=False),

            # R484 - Ponts roulants
            Categorie(famille_id=r484.id, code="1",       libelle="Ponts roulants de cat 1",                      ut_pratique=0.75, pepci_habilite=False),
            Categorie(famille_id=r484.id, code="2",       libelle="Ponts roulants de cat 2",                      ut_pratique=0.75, pepci_habilite=False),
            Categorie(famille_id=r484.id, code="OPT-SOL", libelle="Option Commande au Sol",                       ut_pratique=0.5,  pepci_habilite=False, est_option=True),

            # R485 - Gerbeurs
            Categorie(famille_id=r485.id, code="1",       libelle="Gerbeurs cat 1",                               ut_pratique=0.75, pepci_habilite=False),
            Categorie(famille_id=r485.id, code="2",       libelle="Gerbeurs cat 2",                               ut_pratique=0.75, pepci_habilite=False),

            # R486 - PEMP
            Categorie(famille_id=r486.id, code="A",       libelle="PEMP du groupe A",                             ut_pratique=1.0,  pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r486.id, code="B",       libelle="PEMP du groupe B",                             ut_pratique=1.0,  pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r486.id, code="C",       libelle="PEMP du groupe C",                             ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r486.id, code="OPT-PE",  libelle="Option Porte-Engins PEMP",                     ut_pratique=0.5,  pepci_habilite=False, est_option=True),

            # R487 - Grues mobiles
            Categorie(famille_id=r487.id, code="A",       libelle="Grues mobiles cat A",                          ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r487.id, code="B",       libelle="Grues mobiles cat B",                          ut_pratique=1.0,  pepci_habilite=False),

            # R489 - Chariots
            Categorie(famille_id=r489.id, code="1A",      libelle="Transpalettes a conducteur porte",             ut_pratique=0.5,  pepci_habilite=False),
            Categorie(famille_id=r489.id, code="1B",      libelle="Transpalettes et preparateurs commandes",      ut_pratique=0.75, pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r489.id, code="2A",      libelle="Chariots a mat retractable cat 2A",            ut_pratique=0.5,  pepci_habilite=False),
            Categorie(famille_id=r489.id, code="2B",      libelle="Chariots a mat retractable cat 2B",            ut_pratique=0.5,  pepci_habilite=False),
            Categorie(famille_id=r489.id, code="3",       libelle="Chariots elevateurs en porte-a-faux",          ut_pratique=1.0,  pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r489.id, code="4",       libelle="Chariots a mat retractable cat 4",             ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r489.id, code="5",       libelle="Chariots elevateurs a mat retractable",        ut_pratique=0.75, pepci_habilite=True,  date_habilitation=date(2022,6,14)),
            Categorie(famille_id=r489.id, code="6",       libelle="Chariots a plateau porteur",                   ut_pratique=0.75, pepci_habilite=False),
            Categorie(famille_id=r489.id, code="7",       libelle="Chariots a mat retractable cat 7",             ut_pratique=0.75, pepci_habilite=False),

            # R490 - Grues de chargement
            Categorie(famille_id=r490.id, code="1",       libelle="Grues de chargement cat 1",                    ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r490.id, code="2",       libelle="Grues de chargement cat 2",                    ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r490.id, code="3",       libelle="Grues de chargement cat 3",                    ut_pratique=1.0,  pepci_habilite=False),
            Categorie(famille_id=r490.id, code="OPT-TEL", libelle="Option Telecommande R490",                     ut_pratique=0.5,  pepci_habilite=False, est_option=True),
        ]
        db.add_all(categories)
        db.flush()

        # === TESTEURS PEPCI ===
        josselin = Testeur(nom="JOSSELIN", prenom="Sebastien", statut="interne", numero_inrs="D-552-06", date_habilitation=date(2023,7,12), actif=True)
        nicoise = Testeur(nom="NICOISE", prenom="Gary", statut="interne", numero_inrs="D-552-06", date_habilitation=date(2024,5,13), actif=True)
        db.add_all([josselin, nicoise])
        db.flush()

        # === HABILITATIONS ===
        habilitations = [
            HabilitationTesteur(testeur_id=josselin.id, famille="R482", categorie="A",   option_pe=True, option_tel=True, date_integration=date(2023,7,12)),
            HabilitationTesteur(testeur_id=josselin.id, famille="R482", categorie="B1",  option_pe=True, date_integration=date(2023,7,12)),
            HabilitationTesteur(testeur_id=josselin.id, famille="R482", categorie="C1",  date_integration=date(2023,7,12)),
            HabilitationTesteur(testeur_id=josselin.id, famille="R482", categorie="F",   date_integration=date(2023,7,12)),
            HabilitationTesteur(testeur_id=josselin.id, famille="R489", categorie="1B",  date_integration=date(2025,6,24)),
            HabilitationTesteur(testeur_id=josselin.id, famille="R489", categorie="3",   date_integration=date(2025,6,24)),
            HabilitationTesteur(testeur_id=nicoise.id,  famille="R482", categorie="A",   option_pe=True, option_tel=True, date_integration=date(2024,5,13)),
            HabilitationTesteur(testeur_id=nicoise.id,  famille="R482", categorie="B1",  option_pe=True, date_integration=date(2024,5,13)),
            HabilitationTesteur(testeur_id=nicoise.id,  famille="R482", categorie="C1",  date_integration=date(2024,5,13)),
            HabilitationTesteur(testeur_id=nicoise.id,  famille="R482", categorie="F",   date_integration=date(2024,5,13)),
            HabilitationTesteur(testeur_id=nicoise.id,  famille="R486", categorie="A",   date_integration=date(2024,5,13)),
            HabilitationTesteur(testeur_id=nicoise.id,  famille="R486", categorie="B",   date_integration=date(2024,5,13)),
            HabilitationTesteur(testeur_id=nicoise.id,  famille="R487", categorie="A",   date_integration=date(2024,5,13)),
        ]
        for h in habilitations:
            db.add(h)
            db.flush()
        db.commit()
        print("Donnees initialisees avec succes !")

    except Exception as e:
        print(f"Erreur : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_data()