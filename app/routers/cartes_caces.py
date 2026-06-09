import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import or_, and_
from typing import Optional
from pydantic import BaseModel
from datetime import date
from app.database import get_db
from app.models.carte_caces import CarteCaces
from app.models.caces_obtenu import CacesObtenu
from app.models.stagiaire import Stagiaire
from app.models.session_epreuve import SessionEpreuve
from app.models.testeur import Testeur
from app.models.config_organisme import ConfigOrganisme
from app.models.categorie import Categorie, Famille
from app.models.document_officiel import DocumentOfficiel

router = APIRouter(prefix="/api/cartes-caces", tags=["Cartes CACES®"])

PIN_ADMIN = "1505"


class AnnulerData(BaseModel):
    motif: Optional[str] = None


def _gen_numero(db: DBSession) -> str:
    yy = date.today().strftime("%y")
    prefix = f"PEPCI-{yy}-"
    existing = db.query(CarteCaces).filter(CarteCaces.numero_carte.like(prefix + "%")).all()
    max_n = 0
    for c in existing:
        try:
            n = int(c.numero_carte.rsplit("-", 1)[1])
            if n > max_n:
                max_n = n
        except Exception:
            pass
    return f"{prefix}{max_n + 1:05d}"


def _testeurs_map(cos: list, db: DBSession) -> dict:
    if not cos:
        return {}
    filtre = or_(*[
        and_(
            SessionEpreuve.stagiaire_id == co.stagiaire_id,
            SessionEpreuve.session_id == co.session_id,
            SessionEpreuve.categorie == co.categorie,
            SessionEpreuve.obtenue == True,
        )
        for co in cos
    ])
    epreuves = db.query(SessionEpreuve).filter(filtre).all()
    t_ids = {ep.testeur_id for ep in epreuves if ep.testeur_id}
    testeurs = {t.id: t for t in db.query(Testeur).filter(Testeur.id.in_(t_ids)).all()} if t_ids else {}
    result = {}
    for ep in epreuves:
        k = (ep.stagiaire_id, ep.session_id, ep.categorie)
        t = testeurs.get(ep.testeur_id)
        result[k] = f"{t.nom} {t.prenom}" if t else ""
    return result


def _img_uri(b64, nom):
    if not b64:
        return ""
    ext = (nom or "").rsplit(".", 1)[-1].lower() if nom and "." in (nom or "") else "png"
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/png")
    return f"data:{mime};base64,{b64}"


def _build_verify_url(cfg, numero_carte: str) -> str:
    base = (cfg.url_verification_caces if cfg and cfg.url_verification_caces
            else "https://caces-app.onrender.com/verifier/")
    return base.rstrip('/') + '/' + numero_carte


def _build_print_data(carte, s, cos, t_map, config, famille_libelle="", numero_certificat=""):
    cfg = config or ConfigOrganisme()
    return {
        "id": carte.id,
        "numero_carte": carte.numero_carte,
        "date_generation": carte.date_generation.isoformat(),
        "stagiaire_id": s.id,
        "stagiaire_nom": s.nom,
        "stagiaire_prenom": s.prenom,
        "stagiaire_ddn": s.date_naissance.strftime("%d/%m/%Y") if s.date_naissance else "",
        "photo_url": s.photo or "",
        "famille": carte.famille,
        "famille_libelle": famille_libelle,
        "caces": [
            {
                "categorie": co.categorie,
                "numero_ordre": co.numero_ordre,
                "options_obtenues": co.options_obtenues or "",
                "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
                "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
                "testeur_nom": t_map.get((co.stagiaire_id, co.session_id, co.categorie), ""),
            }
            for co in sorted(cos, key=lambda x: x.categorie)
        ],
        "config": {
            "nom_organisme": cfg.nom_organisme or "",
            "logo_uri": _img_uri(cfg.logo_base64, cfg.logo_nom),
            "signature_uri": _img_uri(cfg.signature_base64, cfg.signature_nom) if hasattr(cfg, 'signature_base64') else "",
            "verify_url": _build_verify_url(cfg, carte.numero_carte),
            "adresse": cfg.adresse or "" if hasattr(cfg, 'adresse') else "",
            "siret": cfg.siret or "" if hasattr(cfg, 'siret') else "",
            "email": cfg.email or "" if hasattr(cfg, 'email') else "",
            "telephone": cfg.telephone or "" if hasattr(cfg, 'telephone') else "",
            "signataire_nom": cfg.signataire_nom or "" if hasattr(cfg, 'signataire_nom') else "",
            "signataire_prenom": cfg.signataire_prenom or "" if hasattr(cfg, 'signataire_prenom') else "",
            "signataire_qualite": cfg.signataire_qualite or "" if hasattr(cfg, 'signataire_qualite') else "",
            "numero_certificat": numero_certificat,
            "logo2_uri": _img_uri(cfg.logo2_base64, cfg.logo2_nom) if hasattr(cfg, 'logo2_base64') else "",
        },
    }


# ===== LECTURE =====

@router.get("/stagiaires")
def get_stagiaires(db: DBSession = Depends(get_db)):
    stagiaires = (
        db.query(Stagiaire)
        .filter(Stagiaire.actif == 1)
        .order_by(Stagiaire.nom, Stagiaire.prenom)
        .all()
    )
    return [{"id": s.id, "nom": s.nom, "prenom": s.prenom,
             "date_naissance": s.date_naissance.isoformat() if s.date_naissance else None}
            for s in stagiaires]


@router.get("/familles/{stagiaire_id}")
def get_familles(stagiaire_id: int, db: DBSession = Depends(get_db)):
    rows = db.query(CacesObtenu.famille).filter(
        CacesObtenu.stagiaire_id == stagiaire_id,
        CacesObtenu.statut == "valide",
    ).distinct().all()
    return sorted([r[0] for r in rows])


@router.get("/caces-valides/{stagiaire_id}/{famille}")
def get_caces_valides(stagiaire_id: int, famille: str, db: DBSession = Depends(get_db)):
    s = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    if not s:
        raise HTTPException(status_code=404)
    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == stagiaire_id, CacesObtenu.famille == famille, CacesObtenu.statut == "valide")
        .order_by(CacesObtenu.categorie)
        .all()
    )
    # Libellés des catégories pour cette famille
    fam_obj = db.query(Famille).filter(Famille.code == famille).first()
    libelles: dict = {}
    if fam_obj:
        cats = db.query(Categorie).filter(Categorie.famille_id == fam_obj.id).all()
        libelles = {c.code: c.libelle or "" for c in cats}

    t_map = _testeurs_map(cos, db)
    return {
        "stagiaire_id": s.id,
        "stagiaire_nom": s.nom,
        "stagiaire_prenom": s.prenom,
        "photo_url": s.photo or "",
        "photo_manquante": not bool(s.photo),
        "famille": famille,
        "caces": [
            {
                "id": co.id,
                "categorie": co.categorie,
                "categorie_libelle": libelles.get(co.categorie, ""),
                "numero_ordre": co.numero_ordre,
                "options_obtenues": co.options_obtenues or "",
                "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
                "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
                "testeur_nom": t_map.get((co.stagiaire_id, co.session_id, co.categorie), ""),
            }
            for co in cos
        ],
    }


@router.get("/{carte_id}/caces")
def get_caces_carte(carte_id: int, db: DBSession = Depends(get_db)):
    carte = db.query(CarteCaces).filter(CarteCaces.id == carte_id).first()
    if not carte:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    # Snapshot stocké à l'émission — retourner directement si disponible
    if carte.caces_json:
        return json.loads(carte.caces_json)
    # Fallback pour les cartes legacy sans snapshot
    cos = (
        db.query(CacesObtenu)
        .filter(
            CacesObtenu.stagiaire_id == carte.stagiaire_id,
            CacesObtenu.famille == carte.famille,
            CacesObtenu.statut == "valide",
        )
        .order_by(CacesObtenu.categorie)
        .all()
    )
    t_map = _testeurs_map(cos, db)
    fam_obj = db.query(Famille).filter(Famille.code == carte.famille).first()
    libelles: dict = {}
    if fam_obj:
        cats = db.query(Categorie).filter(Categorie.famille_id == fam_obj.id).all()
        libelles = {c.code: c.libelle or "" for c in cats}
    return [
        {
            "categorie": co.categorie,
            "categorie_libelle": libelles.get(co.categorie, ""),
            "numero_ordre": co.numero_ordre,
            "options_obtenues": co.options_obtenues or "",
            "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
            "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
            "testeur_nom": t_map.get((co.stagiaire_id, co.session_id, co.categorie), ""),
        }
        for co in cos
    ]


@router.get("/emises")
def get_emises(db: DBSession = Depends(get_db)):
    cartes = (
        db.query(CarteCaces)
        .filter(CarteCaces.statut.in_(["emise", "remplacee", "annulee"]))
        .order_by(CarteCaces.date_generation.desc())
        .all()
    )
    if not cartes:
        return []
    stag_ids = {c.stagiaire_id for c in cartes}
    stagiaires = {s.id: s for s in db.query(Stagiaire).filter(Stagiaire.id.in_(stag_ids)).all()}
    return [
        {
            "id": c.id,
            "stagiaire_id": c.stagiaire_id,
            "stagiaire_nom": stagiaires[c.stagiaire_id].nom if c.stagiaire_id in stagiaires else "?",
            "stagiaire_prenom": stagiaires[c.stagiaire_id].prenom if c.stagiaire_id in stagiaires else "",
            "stagiaire_ddn": stagiaires[c.stagiaire_id].date_naissance.isoformat() if c.stagiaire_id in stagiaires and stagiaires[c.stagiaire_id].date_naissance else None,
            "famille": c.famille,
            "numero_carte": c.numero_carte,
            "date_generation": c.date_generation.isoformat(),
            "statut": c.statut,
            "motif_annulation": c.motif_annulation or "",
        }
        for c in cartes
    ]


@router.get("/reimprimer/{carte_id}")
def reimprimer_carte(carte_id: int, db: DBSession = Depends(get_db)):
    carte = db.query(CarteCaces).filter(CarteCaces.id == carte_id).first()
    if not carte:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    s = db.query(Stagiaire).filter(Stagiaire.id == carte.stagiaire_id).first()
    if not s:
        raise HTTPException(status_code=404)
    config = db.query(ConfigOrganisme).first()
    cfg = config or ConfigOrganisme()
    doc_cert = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == "certificat_organisme").first()
    numero_certificat = doc_cert.numero_certificat or "" if doc_cert else ""

    fam_obj = db.query(Famille).filter(Famille.code == carte.famille).first()
    famille_libelle = fam_obj.libelle if fam_obj else ""

    if carte.caces_json:
        # Snapshot figé à l'émission — impression fidèle à l'original
        return {
            "id": carte.id,
            "numero_carte": carte.numero_carte,
            "date_generation": carte.date_generation.isoformat(),
            "stagiaire_id": s.id,
            "stagiaire_nom": s.nom,
            "stagiaire_prenom": s.prenom,
            "stagiaire_ddn": s.date_naissance.strftime("%d/%m/%Y") if s.date_naissance else "",
            "photo_url": s.photo or "",
            "famille": carte.famille,
            "famille_libelle": famille_libelle,
            "caces": json.loads(carte.caces_json),
            "config": {
                "nom_organisme": cfg.nom_organisme or "",
                "logo_uri": _img_uri(cfg.logo_base64, cfg.logo_nom),
                "signature_uri": _img_uri(cfg.signature_base64, cfg.signature_nom) if hasattr(cfg, 'signature_base64') else "",
                "verify_url": _build_verify_url(cfg, carte.numero_carte),
                "adresse": cfg.adresse or "" if hasattr(cfg, 'adresse') else "",
                "siret": cfg.siret or "" if hasattr(cfg, 'siret') else "",
                "email": cfg.email or "" if hasattr(cfg, 'email') else "",
                "telephone": cfg.telephone or "" if hasattr(cfg, 'telephone') else "",
                "signataire_nom": cfg.signataire_nom or "" if hasattr(cfg, 'signataire_nom') else "",
                "signataire_prenom": cfg.signataire_prenom or "" if hasattr(cfg, 'signataire_prenom') else "",
                "signataire_qualite": cfg.signataire_qualite or "" if hasattr(cfg, 'signataire_qualite') else "",
                "numero_certificat": numero_certificat,
                "logo2_uri": _img_uri(cfg.logo2_base64, cfg.logo2_nom) if hasattr(cfg, 'logo2_base64') else "",
            },
        }

    # Fallback legacy : CACES® valides actuels
    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == carte.stagiaire_id, CacesObtenu.famille == carte.famille, CacesObtenu.statut == "valide")
        .all()
    )
    t_map = _testeurs_map(cos, db)
    fam_obj = db.query(Famille).filter(Famille.code == carte.famille).first()
    famille_libelle = fam_obj.libelle if fam_obj else ""
    return _build_print_data(carte, s, cos, t_map, config, famille_libelle, numero_certificat)


# ===== ACTIONS =====

@router.post("/emettre/{stagiaire_id}/{famille}")
def emettre_carte(stagiaire_id: int, famille: str, pin: str = "", db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    s = db.query(Stagiaire).filter(Stagiaire.id == stagiaire_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire introuvable")
    if not s.photo:
        raise HTTPException(status_code=400, detail="Photo manquante — impossible d'émettre la carte")
    cos = (
        db.query(CacesObtenu)
        .filter(CacesObtenu.stagiaire_id == stagiaire_id, CacesObtenu.famille == famille, CacesObtenu.statut == "valide")
        .all()
    )
    if not cos:
        raise HTTPException(status_code=400, detail="Aucun CACES® valide pour ce stagiaire / famille")

    # Snapshot figé à l'émission
    t_map = _testeurs_map(cos, db)
    fam_obj = db.query(Famille).filter(Famille.code == famille).first()
    libelles: dict = {}
    if fam_obj:
        libelles = {c.code: c.libelle or "" for c in db.query(Categorie).filter(Categorie.famille_id == fam_obj.id).all()}
    caces_snapshot = json.dumps([
        {
            "categorie": co.categorie,
            "categorie_libelle": libelles.get(co.categorie, ""),
            "numero_ordre": co.numero_ordre,
            "options_obtenues": co.options_obtenues or "",
            "date_obtention": co.date_obtention.isoformat() if co.date_obtention else None,
            "date_echeance": co.date_echeance.isoformat() if co.date_echeance else None,
            "testeur_nom": t_map.get((co.stagiaire_id, co.session_id, co.categorie), ""),
        }
        for co in sorted(cos, key=lambda x: x.categorie)
    ], ensure_ascii=False)

    # Remplace l'ancienne carte émise
    db.query(CarteCaces).filter(
        CarteCaces.stagiaire_id == stagiaire_id,
        CarteCaces.famille == famille,
        CarteCaces.statut == "emise",
    ).update({"statut": "remplacee"})
    carte = CarteCaces(
        stagiaire_id=stagiaire_id,
        famille=famille,
        numero_carte=_gen_numero(db),
        date_generation=date.today(),
        statut="emise",
        caces_json=caces_snapshot,
    )
    db.add(carte)
    db.commit()
    db.refresh(carte)
    config = db.query(ConfigOrganisme).first()
    doc_cert = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == "certificat_organisme").first()
    numero_certificat = doc_cert.numero_certificat or "" if doc_cert else ""
    famille_libelle = fam_obj.libelle if fam_obj else ""
    return _build_print_data(carte, s, cos, t_map, config, famille_libelle, numero_certificat)


def _generate_cr80_pdf(carte, s, cfg, caces_list: list, verify_url: str) -> bytes:
    """Génère un PDF CR80 recto/verso avec reportlab."""
    import base64 as _b64
    from io import BytesIO as _BIO
    import qrcode as _qr
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Table, TableStyle

    W, H = 85.6 * mm, 54.0 * mm
    RED = colors.HexColor('#c62828')
    ANT = colors.HexColor('#2b2b2b')
    GRAY = colors.HexColor('#f0f0f0')

    buf = _BIO()
    c = Canvas(buf, pagesize=(W, H))

    # ── RECTO ──────────────────────────────────────────────────────────────
    # Footer strip
    c.setFillColor(GRAY)
    c.rect(0, 0, W, 4 * mm, fill=1, stroke=0)
    c.setFillColor(RED)
    c.rect(0, 0, W, 1.5 * mm, fill=1, stroke=0)

    # Org/signature text in footer
    org_name = (cfg.nom_organisme or '') if cfg else ''
    c.setFont('Helvetica-Bold', 4.5)
    c.setFillColor(ANT)
    c.drawString(2 * mm, 2.7 * mm, org_name)
    sig = ''
    if cfg and getattr(cfg, 'signataire_nom', None):
        sig = f"{cfg.signataire_prenom or ''} {cfg.signataire_nom}".strip()
        if getattr(cfg, 'signataire_qualite', None):
            sig += f" — {cfg.signataire_qualite}"
    if sig:
        c.setFont('Helvetica', 4)
        c.drawString(2 * mm, 1.8 * mm, sig)

    # Header (top 15mm), red border-bottom
    c.setStrokeColor(RED)
    c.setLineWidth(0.5)
    c.line(0, H - 15 * mm, W, H - 15 * mm)

    # Logo organisme
    if cfg and getattr(cfg, 'logo_base64', None):
        try:
            logo_data = _b64.b64decode(cfg.logo_base64)
            logo_rdr = ImageReader(_BIO(logo_data))
            c.drawImage(logo_rdr, 2 * mm, H - 14 * mm, width=24 * mm, height=12 * mm,
                        preserveAspectRatio=True, anchor='nw', mask='auto')
        except Exception:
            c.setFont('Helvetica-Bold', 6)
            c.setFillColor(ANT)
            c.drawString(2 * mm, H - 8 * mm, org_name or 'CACES®')

    # Assurance Maladie logo
    try:
        c.drawImage('static/img/assurance_maladie_caces.jpeg',
                    W - 28 * mm, H - 14.5 * mm, width=26 * mm, height=13 * mm,
                    preserveAspectRatio=True, anchor='nw', mask='auto')
    except Exception:
        pass

    # DEKRA cert
    numeroCert = ''
    if cfg and getattr(cfg, 'numero_certificat', None):
        numeroCert = cfg.numero_certificat
    if numeroCert:
        c.setFont('Helvetica-Bold', 3.8)
        c.setFillColor(ANT)
        c.drawString(2 * mm, H - 15.5 * mm, f'Cert. DEKRA n° {numeroCert}')

    # Sub-header "Certificat d'aptitude..."
    c.setFont('Helvetica-Oblique', 5.5)
    c.setFillColor(ANT)
    c.drawString(2 * mm, H - 17.5 * mm, "Certificat d'aptitude à la conduite en sécurité")
    c.setStrokeColor(colors.HexColor('#e4e4e4'))
    c.setLineWidth(0.3)
    c.line(0, H - 18.5 * mm, W, H - 18.5 * mm)

    # Body area
    body_top = H - 19 * mm  # y coord of top of body
    right_w = 13 * mm
    right_x = W - right_w - 1.5 * mm

    # CACES® family badge
    badge_h = 3.5 * mm
    c.setFillColor(RED)
    c.roundRect(2 * mm, body_top - badge_h, 52 * mm, badge_h, 0.7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 6)
    fam_label = f"CACES® {carte.famille}"
    c.drawString(3 * mm, body_top - badge_h + 0.8 * mm, fam_label)

    # N° CACES
    nums = [f"{co.get('numero_ordre', 0):04d}" for co in caces_list if co.get('numero_ordre')]
    if nums:
        c.setFont('Helvetica-Bold', 7.5)
        c.setFillColor(RED)
        c.drawString(2 * mm, body_top - 7.5 * mm, f"N° {' · '.join(nums)}")

    # Name
    nom = f"{s.nom.upper()} {s.prenom}"
    if len(nom) > 24:
        nom = nom[:23] + '…'
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(ANT)
    c.drawString(2 * mm, body_top - 12 * mm, nom)

    # DOB
    if s.date_naissance:
        c.setFont('Helvetica-Oblique', 6.5)
        c.drawString(2 * mm, body_top - 15.5 * mm, f"Né(e) le {s.date_naissance.strftime('%d/%m/%Y')}")

    # Right column: photo
    photo_h, photo_w = 12 * mm, 11 * mm
    photo_x = right_x + (right_w - photo_w) / 2
    photo_y = body_top - photo_h
    photo_drawn = False
    if s.photo:
        try:
            import requests as _req
            resp = _req.get(s.photo, timeout=5)
            if resp.status_code == 200:
                photo_rdr = ImageReader(_BIO(resp.content))
                c.drawImage(photo_rdr, photo_x, photo_y, width=photo_w, height=photo_h,
                            preserveAspectRatio=False, mask='auto')
                c.setStrokeColor(colors.HexColor('#bbbbbb'))
                c.setLineWidth(0.4)
                c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)
                photo_drawn = True
        except Exception:
            pass
    if not photo_drawn:
        c.setFillColor(colors.HexColor('#eeeeee'))
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)

    # Separator
    sep_y = photo_y - 0.6 * mm
    c.setStrokeColor(colors.HexColor('#d0d0d0'))
    c.setLineWidth(0.3)
    c.line(right_x, sep_y, right_x + right_w, sep_y)

    # QR code
    qr_size = 10 * mm
    qr_y = sep_y - qr_size - 0.4 * mm
    qr_x = right_x + (right_w - qr_size) / 2
    try:
        qr_img = _qr.make(verify_url or carte.numero_carte)
        qr_buf = _BIO()
        qr_img.save(qr_buf, format='PNG')
        qr_buf.seek(0)
        c.drawImage(ImageReader(qr_buf), qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')
    except Exception:
        pass

    # QR label
    c.setFont('Helvetica-Oblique', 3.5)
    c.setFillColor(ANT)
    c.drawCentredString(right_x + right_w / 2, qr_y - 1.5 * mm, 'Scanner · Vérifier')

    # Recto footer text
    c.setFont('Helvetica-Oblique', 3.3)
    c.setFillColor(colors.HexColor('#555555'))
    c.drawCentredString(W / 2, 0.8 * mm, "La marque CACES® est protégée (INPI n° 03.3237295) · Document recto/verso obligatoire")

    c.showPage()

    # ── VERSO ──────────────────────────────────────────────────────────────
    # Red top strip + red header border-bottom
    c.setFillColor(RED)
    c.rect(0, H - 1.5 * mm, W, 1.5 * mm, fill=1, stroke=0)
    c.setStrokeColor(RED)
    c.setLineWidth(0.7)
    c.line(0, H - 9.5 * mm, W, H - 9.5 * mm)

    c.setFont('Helvetica-Bold', 5.5)
    c.setFillColor(ANT)
    titre = f"CACES® {carte.famille} — {s.nom} {s.prenom}"
    if s.date_naissance:
        titre += f" ({s.date_naissance.strftime('%d/%m/%Y')})"
    c.drawString(2 * mm, H - 5.5 * mm, titre)
    c.setFont('Courier-Bold', 4.8)
    c.setFillColor(RED)
    c.drawString(2 * mm, H - 8.8 * mm, f"N° {carte.numero_carte}")

    # CACES® table
    from datetime import datetime as _dtv
    def _fd(iso):
        if not iso:
            return '—'
        try:
            return _dtv.fromisoformat(iso[:10]).strftime('%d/%m/%y')
        except Exception:
            return iso

    headers = ['Fam.', 'Cat.', 'Opt.', 'N° CACES®', 'Obtention', 'Échéance', 'Testeur']
    rows = [headers]
    for co in caces_list:
        no = f"{co['numero_ordre']:04d}" if co.get('numero_ordre') else '—'
        rows.append([
            carte.famille,
            co.get('categorie', ''),
            co.get('options_obtenues', '') or '—',
            no,
            _fd(co.get('date_obtention')),
            _fd(co.get('date_echeance')),
            (co.get('testeur_nom') or '—')[:18],
        ])

    col_widths = [7 * mm, 7 * mm, 11 * mm, 13 * mm, 13 * mm, 13 * mm, None]
    col_widths[-1] = W - 4 * mm - sum(w for w in col_widths[:-1])

    tbl = Table(rows, colWidths=col_widths, rowHeights=None)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ANT),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 3.8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 4.3),
        ('FONTNAME', (3, 1), (3, -1), 'Courier-Bold'),
        ('FONTSIZE', (3, 1), (3, -1), 4.3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 1.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('GRID', (0, 0), (-1, -1), 0.1, colors.HexColor('#e0e0e0')),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#555555')),
    ]))
    tbl_w, tbl_h = tbl.wrapOn(c, W - 4 * mm, H)
    tbl.drawOn(c, 2 * mm, H - 10.5 * mm - tbl_h)

    # Verso footer
    c.setFillColor(GRAY)
    c.rect(0, 0, W, 3.5 * mm, fill=1, stroke=0)
    c.setFont('Helvetica-Oblique', 3.3)
    c.setFillColor(colors.HexColor('#555555'))
    if verify_url:
        c.drawCentredString(W / 2, 1.5 * mm, f'Vérification : {verify_url}')
    c.drawCentredString(W / 2, 0.4 * mm, 'Document recto/verso · Toute copie doit comporter les 2 faces')

    c.save()
    return buf.getvalue()


def _protect_pdf(pdf_bytes: bytes, owner_password: str = "NORYX-CACES-PEPCI") -> bytes:
    """Chiffre le PDF : impression autorisée, modification interdite."""
    from io import BytesIO as _BIO
    from pypdf import PdfWriter, PdfReader
    reader = PdfReader(_BIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    # permissions_flag : bit 3 (print=4) + bit 12 (print high quality=2048) = 2052
    writer.encrypt(
        user_password="",
        owner_password=owner_password,
        use_128bit=True,
        permissions_flag=2052,
    )
    out = _BIO()
    writer.write(out)
    out.seek(0)
    return out.read()


@router.get("/{carte_id}/pdf")
def telecharger_pdf(carte_id: int, db: DBSession = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    from io import BytesIO as _BIO
    carte = db.query(CarteCaces).filter(CarteCaces.id == carte_id).first()
    if not carte:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    s = db.query(Stagiaire).filter(Stagiaire.id == carte.stagiaire_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Stagiaire introuvable")
    config = db.query(ConfigOrganisme).first()
    cfg = config or ConfigOrganisme()
    caces_list = json.loads(carte.caces_json) if carte.caces_json else []
    verify_url = _build_verify_url(cfg, carte.numero_carte)
    pdf_bytes = _generate_cr80_pdf(carte, s, cfg, caces_list, verify_url)
    protected = _protect_pdf(pdf_bytes)
    filename = f"CACES-{carte.numero_carte}.pdf"
    return StreamingResponse(
        _BIO(protected),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(protected)),
        }
    )


@router.post("/annuler/{carte_id}")
def annuler_carte(carte_id: int, pin: str = "", data: Optional[AnnulerData] = Body(default=None), db: DBSession = Depends(get_db)):
    if pin != PIN_ADMIN:
        raise HTTPException(status_code=403, detail="PIN incorrect")
    carte = db.query(CarteCaces).filter(CarteCaces.id == carte_id).first()
    if not carte:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    carte.statut = "annulee"
    carte.motif_annulation = data.motif if data and data.motif else None
    db.commit()
    return {"ok": True}
