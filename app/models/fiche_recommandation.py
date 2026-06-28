from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class FicheRecommandation(Base):
    """Fiche de recommandation de formation complémentaire remise au candidat
    qui a échoué à la théorie et/ou à des pratiques dans une session.

    États : brouillon (modifiable librement, pré-rempli depuis les résultats)
            -> finalisee (enregistrée, document remis).
    Après finalisation : MODIFIABLE (rouvrir, PIN) et SUPPRIMABLE (PIN admin),
    comme les autres documents. PAS de verrou immuable façon carte CACES®.

    Une fiche par (session, candidat).
    """
    __tablename__ = "fiche_recommandation"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    stagiaire_id = Column(Integer, ForeignKey("stagiaires.id"), nullable=False)

    statut = Column(String(20), nullable=False, default="brouillon")  # brouillon | finalisee

    # Saisies du testeur (cases "précisions sur l'échec")
    fraude_theorie = Column(Boolean, default=False, nullable=False)
    difficultes_langue = Column(Boolean, default=False, nullable=False)
    comportement_dangereux = Column(Boolean, default=False, nullable=False)
    autres_precisions = Column(Text, nullable=True)

    # Durées ajustées + causes modifiées par le testeur (JSON, garde la souplesse).
    # Structure libre : { "theorie": "<duree>", "pratiques": { "B1": {"duree": "...", "cause": "..."} } }
    saisies_json = Column(Text, nullable=True)

    # Instantané des résultats au moment de la finalisation (cohérence du document remis).
    snapshot_json = Column(Text, nullable=True)

    testeur_id = Column(Integer, ForeignKey("testeurs.id"), nullable=True)
    testeur_nom = Column(String(120), nullable=True)

    date_creation = Column(DateTime, server_default=func.now())
    date_maj = Column(DateTime, server_default=func.now(), onupdate=func.now())
    date_finalisation = Column(DateTime, nullable=True)