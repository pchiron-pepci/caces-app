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
        "photo_url": (s.photo_base64 and f"data:image/jpeg;base64,{s.photo_base64}") or s.photo or "",
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
        "photo_url": (s.photo_base64 and f"data:image/jpeg;base64,{s.photo_base64}") or s.photo or "",
        "photo_manquante": not bool(s.photo_base64 or s.photo),
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
            "photo_url": (s.photo_base64 and f"data:image/jpeg;base64,{s.photo_base64}") or s.photo or "",
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
    if not s.photo_base64 and not s.photo:
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


def _render_cr80_html(carte, s, cfg, caces_list, verify_url, famille_libelle='', numero_certificat=''):
    """Genere le HTML CR80 recto/verso identique au template JS, pour WeasyPrint."""
    import base64 as _b64
    from io import BytesIO as _BIO
    import qrcode as _qr
    from html import escape as _esc

    ANT = '#2b2b2b'
    RED = '#c62828'

    # QR code -> PNG base64
    qr = _qr.QRCode(version=1, box_size=4, border=1,
                    error_correction=_qr.constants.ERROR_CORRECT_M)
    qr.add_data(verify_url or carte.numero_carte)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=ANT, back_color='white')
    qr_buf = _BIO()
    qr_img.save(qr_buf, format='PNG')
    qr_b64 = _b64.b64encode(qr_buf.getvalue()).decode()
    qr_html = f'<img class="r-qr" src="data:image/png;base64,{qr_b64}">'

    # Photo -> photo_base64 (DB) en priorité, fallback chemin fichier local
    photo_html = '<div class="r-photo-ph"></div>'
    _src = None
    if s.photo_base64:
        _src = f'data:image/jpeg;base64,{s.photo_base64}'
    elif s.photo and s.photo.startswith('/'):
        import os as _os
        _fs = '.' + s.photo
        if _os.path.exists(_fs):
            try:
                with open(_fs, 'rb') as _f:
                    _raw = _f.read()
                _ext = s.photo.rsplit('.', 1)[-1].lower() if '.' in s.photo else 'jpg'
                _ct = 'image/jpeg' if _ext in ('jpg', 'jpeg') else f'image/{_ext}'
                _src = f'data:{_ct};base64,{_b64.b64encode(_raw).decode()}'
            except Exception:
                pass
    if _src:
        photo_html = (
            f'<img style="width:18mm;height:22mm;display:block;'
            f'border:0.4mm solid #bbb;border-radius:0.6mm;" src="{_src}">'
        )

    # Logo organisme
    if cfg and cfg.logo_base64:
        ext = (cfg.logo_nom or '').rsplit('.', 1)[-1].lower() if cfg.logo_nom and '.' in (cfg.logo_nom or '') else 'png'
        mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else 'image/png'
        logo_html = f'<img class="r-logo" src="data:{mime};base64,{cfg.logo_base64}">'
    else:
        org = _esc((cfg.nom_organisme or 'CACES®') if cfg else 'CACES®')
        logo_html = f'<span style="font-size:5.5pt;font-weight:900;color:{ANT};">{org}</span>'

    # AM logo
    am_html = ''
    try:
        with open('static/img/assurance_maladie_caces.jpeg', 'rb') as f:
            am_b64 = _b64.b64encode(f.read()).decode()
        am_html = f'<img class="r-logo-am" src="data:image/jpeg;base64,{am_b64}">'
    except Exception:
        pass

    # Signature
    sign_html = ''
    if cfg and getattr(cfg, 'signature_base64', None):
        sig_ext = (getattr(cfg, 'signature_nom', '') or '').rsplit('.', 1)[-1].lower()
        sig_mime = 'image/jpeg' if sig_ext in ('jpg', 'jpeg') else 'image/png'
        sign_html = f'<img src="data:{sig_mime};base64,{cfg.signature_base64}" style="height:3.5mm;width:auto;max-width:8mm;object-fit:contain;"> '

    sig_nom = ' '.join(filter(None, [getattr(cfg, 'signataire_prenom', '') or '', getattr(cfg, 'signataire_nom', '') or ''])) if cfg else ''
    sig_qualite = (getattr(cfg, 'signataire_qualite', '') or '') if cfg else ''
    sig_ligne = ' — '.join(filter(None, [sig_nom, sig_qualite]))

    organisme = _esc((cfg.nom_organisme or '') if cfg else '')
    adresse = _esc((getattr(cfg, 'adresse', '') or '') if cfg else '')
    delivree_par = f'{organisme} — {adresse}' if adresse else organisme
    siret_parts = [
        f"SIRET {_esc(cfg.siret)}" if cfg and getattr(cfg, 'siret', '') else '',
        _esc((getattr(cfg, 'email', '') or '') if cfg else ''),
        f"Tél. {_esc(cfg.telephone)}" if cfg and getattr(cfg, 'telephone', '') else '',
    ]
    siret_line = ' · '.join(p for p in siret_parts if p)

    nums_caces = ' – '.join(
        str(co.get('numero_ordre', '')).zfill(4)
        for co in caces_list if co.get('numero_ordre')
    )

    all_opts: dict = {}
    for co in caces_list:
        if co.get('options_obtenues'):
            for o in co['options_obtenues'].split(','):
                all_opts[o.strip()] = True
    opt_labels = {'PE': 'Porte-engin', 'TEL': 'Télécommande', 'TE': 'Télécommande',
                  'CC': 'Conduite cabine', 'TR': 'Translation rails', 'CEC': 'Circulation en charge'}
    opt_legend = ' — '.join(f"{k} : {opt_labels.get(k, k)}" for k in all_opts)

    verso_notices_parts = []
    if carte.famille == 'R482':
        verso_notices_parts.append("Option réseaux : Ne permet pas la délivrance d'une AIPR")
    if opt_legend:
        verso_notices_parts.append(f'Options : {opt_legend}')
    verso_notices_html = (
        f'<div class="v-notices">{" — ".join(verso_notices_parts)}</div>'
        if verso_notices_parts else ''
    )

    ddn_str = s.date_naissance.strftime('%d/%m/%Y') if s.date_naissance else ''
    ddn_verso = f' <span class="v-hddn">({_esc(ddn_str)})</span>' if ddn_str else ''
    date_gen_str = carte.date_generation.strftime('%d/%m/%y') if carte.date_generation else ''

    logo2_html = ''
    if cfg and getattr(cfg, 'logo2_base64', None):
        ext2 = (getattr(cfg, 'logo2_nom', '') or '').rsplit('.', 1)[-1].lower()
        mime2 = 'image/jpeg' if ext2 in ('jpg', 'jpeg') else 'image/png'
        logo2_html = f'<img class="v-logo2" src="data:{mime2};base64,{cfg.logo2_base64}">'

    from datetime import datetime as _dtt
    def _fc(iso):
        if not iso: return '—'
        try: return _dtt.fromisoformat(iso[:10]).strftime('%d/%m/%y')
        except: return iso

    verso_rows = ''
    for co in caces_list:
        no = str(co.get('numero_ordre', '')).zfill(4) if co.get('numero_ordre') else '—'
        opts_html = ''
        if co.get('options_obtenues'):
            for o in co['options_obtenues'].split(','):
                opts_html += f'<span class="vopt-badge">{_esc(o.strip())}</span> '
        else:
            opts_html = '<span style="color:#bbb;">—</span>'
        has_test = bool(co.get('testeur_nom'))
        verso_rows += (
            f'<tr{" class=\"vhastest\"" if has_test else ""}>'
            f'<td class="vfam">{_esc(carte.famille)}</td>'
            f'<td class="vcat">{_esc(co.get("categorie", ""))}</td>'
            f'<td class="vopt">{opts_html}</td>'
            f'<td class="vno">{no}</td>'
            f'<td class="vdt">{_fc(co.get("date_obtention"))}</td>'
            f'<td class="vval">{_fc(co.get("date_echeance"))}</td>'
            f'<td class="vlib">{_esc(co.get("categorie_libelle", ""))}</td>'
            f'</tr>'
        )
        if has_test:
            verso_rows += f'<tr><td colspan="7" class="vtestcell">Testeur : {_esc(co.get("testeur_nom", ""))}</td></tr>'

    fam_badge = f'CACES® {_esc(carte.famille)}'
    if famille_libelle:
        fam_badge += f' — {_esc(famille_libelle.upper())}'

    css = (
        f'* {{ margin:0; padding:0; box-sizing:border-box; }}\n'
        f'@page {{ size:85.6mm 54mm; margin:0; }}\n'
        f'html,body {{ width:85.6mm; height:108mm; font-family:Arial,Helvetica,sans-serif; font-size:5.5pt; background:#fff; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}\n'
        f'.page {{ width:85.6mm; height:54mm; overflow:hidden; display:flex; flex-direction:column; }}\n'
        f'.page + .page {{ page-break-before:always; }}\n'
        f'.r-hdr {{ background:#fff; height:15mm; display:flex; align-items:center; padding:0 2.5mm; justify-content:space-between; flex-shrink:0; gap:1.5mm; border-bottom:0.5mm solid {RED}; }}\n'
        f'.r-hdr-left {{ display:flex; flex-direction:column; align-items:flex-start; gap:0.5mm; }}\n'
        f'.r-logo {{ height:11mm; width:auto; max-width:26mm; object-fit:contain; }}\n'
        f'.r-logo-am {{ height:13mm; width:auto; max-width:30mm; object-fit:contain; }}\n'
        f'.r-dekra {{ font-size:4pt; color:{ANT}; font-weight:800; letter-spacing:0.05mm; }}\n'
        f'.r-subhdr {{ background:#fff; border-bottom:0.3mm solid #e4e4e4; padding:0.55mm 2.5mm; display:flex; align-items:center; flex-shrink:0; }}\n'
        f'.r-subhdr-title {{ font-size:6.5pt; color:{ANT}; font-style:italic; }}\n'
        f'.r-body {{ display:flex; flex:1; padding:1.2mm 2.5mm 0; gap:2mm; min-height:0; overflow:hidden; }}\n'
        f'.r-left {{ flex:1; min-width:0; display:flex; flex-direction:column; }}\n'
        f'.r-right {{ width:14.5mm; flex-shrink:0; display:flex; flex-direction:column; align-items:center; gap:0.7mm; padding-top:0.2mm; }}\n'
        f'.r-fam-badge {{ display:inline-block; background:{RED}; color:#fff; font-size:6.5pt; font-weight:900; padding:0.4mm 2mm; border-radius:0.7mm; margin-bottom:0.7mm; letter-spacing:0.1mm; white-space:nowrap; }}\n'
        f'.r-nums {{ font-size:8pt; color:{RED}; font-weight:800; margin-top:1.5mm; margin-bottom:0.4mm; letter-spacing:0.2mm; }}\n'
        f'.r-nums .lbl {{ font-weight:400; color:{ANT}; font-size:6.5pt; }}\n'
        f'.r-titulaire {{ font-size:9pt; font-weight:900; font-style:italic; color:{ANT}; margin-bottom:0.3mm; line-height:1.2; }}\n'
        f'.r-ddn {{ font-size:7pt; color:{ANT}; font-style:italic; }}\n'
        f'.r-spacer {{ flex:1; min-height:0.5mm; }}\n'
        f'.r-org {{ font-size:6pt; color:{ANT}; font-weight:700; line-height:1.25; margin-bottom:0.25mm; }}\n'
        f'.r-siret {{ font-size:5pt; color:{ANT}; margin-bottom:0.35mm; line-height:1.3; }}\n'
        f'.r-sign {{ font-size:5.2pt; color:{ANT}; display:flex; align-items:center; gap:0.8mm; padding-bottom:0.4mm; }}\n'
        f'.r-sign img {{ height:3.5mm; width:auto; max-width:8mm; object-fit:contain; }}\n'
        f'.r-photo {{ width:11mm; height:12mm; border:0.4mm solid #bbb; display:block; border-radius:0.6mm; }}\n'
        f'.r-photo-ph {{ width:22mm; height:28mm; background:#eee; border:0.4mm solid #bbb; border-radius:0.6mm; }}\n'
        f'.r-sep {{ width:11mm; height:0.25mm; background:#d0d0d0; margin:0.4mm 0 0.2mm; flex-shrink:0; }}\n'
        f'.r-qr {{ width:10mm; height:10mm; display:block; }}\n'
        f'.r-qr-text {{ font-size:3.8pt; color:{ANT}; text-align:center; line-height:1.25; font-style:italic; max-width:11mm; }}\n'
        f'.r-ftr {{ flex-shrink:0; background:#f0f0f0; border-top:0.3mm solid #d0d0d0; padding:0.7mm 2.5mm; font-size:5.2pt; color:#111; font-style:italic; text-align:center; line-height:1.3; }}\n'
        f'.v-hdr {{ background:#fff; border-bottom:0.7mm solid {RED}; padding:0.6mm 2.5mm; flex-shrink:0; display:flex; align-items:center; justify-content:space-between; gap:1mm; }}\n'
        f'.v-hdr-info {{ flex:1; min-width:0; }}\n'
        f'.v-htitle {{ font-size:6pt; font-weight:900; color:{ANT}; line-height:1.2; }}\n'
        f'.v-hddn {{ font-size:4.3pt; font-weight:400; color:{ANT}; font-style:italic; }}\n'
        f'.v-hcarte {{ font-size:5.2pt; color:{RED}; font-weight:700; font-family:monospace; margin-top:0.2mm; }}\n'
        f'.v-hdate {{ color:{ANT}; font-weight:400; font-family:Arial,sans-serif; font-size:4.5pt; }}\n'
        f'.v-notices {{ padding:0.5mm 2.5mm; font-size:4.3pt; color:{ANT}; line-height:1.3; flex-shrink:0; border-bottom:0.15mm solid #e0e0e0; }}\n'
        f'.v-tbl {{ flex:1; padding:0 2.5mm; overflow:hidden; }}\n'
        f'.v-logo2 {{ height:6mm; width:auto; max-width:14mm; object-fit:contain; flex-shrink:0; }}\n'
        f'table {{ width:100%; border-collapse:collapse; }}\n'
        f'thead tr {{ background:{ANT}; }}\n'
        f'th {{ font-size:3.8pt; font-weight:700; color:#fff; text-transform:uppercase; padding:0.5mm 0.4mm; text-align:left; white-space:nowrap; letter-spacing:0.04mm; }}\n'
        f'tbody tr:nth-child(even) {{ background:#f5f5f5; }}\n'
        f'td {{ font-size:5.2pt; padding:0.4mm 0.4mm; border-bottom:0.1mm solid #ebebeb; vertical-align:middle; color:{ANT}; }}\n'
        f'.vfam {{ font-weight:800; color:{RED}; font-size:5pt; white-space:nowrap; }}\n'
        f'.vcat {{ font-weight:900; color:{ANT}; font-size:5.2pt; white-space:nowrap; }}\n'
        f'.vno {{ font-family:monospace; font-weight:800; font-size:5pt; white-space:nowrap; color:{ANT}; }}\n'
        f'.vopt-badge {{ display:inline-block; background:#e6e6e6; color:{ANT}; font-size:3.8pt; font-weight:600; padding:0.1mm 0.5mm; border-radius:0.4mm; white-space:nowrap; border:0.15mm solid #c0c0c0; }}\n'
        f'.vdt {{ font-size:4.8pt; white-space:nowrap; color:{ANT}; font-weight:700; }}\n'
        f'.vval {{ font-weight:700; font-size:4.8pt; color:{ANT}; white-space:nowrap; }}\n'
        f'.vopt {{ max-width:9mm; overflow:hidden; }}\n'
        f'.vlib {{ color:{ANT}; font-size:4.2pt; font-style:italic; font-weight:600; }}\n'
        f'.vhastest td {{ border-bottom:none !important; }}\n'
        f'.vtestcell {{ padding:0.3mm 0.4mm 0.5mm !important; font-size:3.8pt; color:{ANT}; font-style:italic; font-weight:600; vertical-align:middle; border-bottom:0.15mm solid #d8d8d8 !important; }}\n'
        f'.v-ftr {{ flex-shrink:0; background:#f0f0f0; border-top:0.3mm solid #d0d0d0; padding:0.6mm 2.5mm; font-size:5.2pt; color:#111; font-style:italic; text-align:center; line-height:1.3; }}'
    )

    ddn_recto = f'<div class="r-ddn">Né(e) le {_esc(ddn_str)}</div>' if ddn_str else ''
    nums_html = f'<div class="r-nums"><span class="lbl">N° CACES® </span>{_esc(nums_caces)}</div>' if nums_caces else ''
    dekra_html = f'<div class="r-dekra">Cert. DEKRA n° {_esc(numero_certificat)}</div>' if numero_certificat else ''
    org_html = f'<div class="r-org">{delivree_par}</div>' if delivree_par else ''
    siret_html = f'<div class="r-siret">{siret_line}</div>' if siret_line else ''
    sign_bloc = f'<div class="r-sign">{sign_html}{_esc(sig_ligne)}</div>' if sig_ligne else ''
    edition_html = f' <span class="v-hdate">· Édition du {_esc(date_gen_str)}</span>' if date_gen_str else ''
    verif_html = f'Vérification : {_esc(verify_url)} — ' if verify_url else ''

    return (
        '<!DOCTYPE html>\n<html><head><meta charset="UTF-8"><style>' + css + '</style></head><body>\n'
        '<div class="page">\n'
        '  <div class="r-hdr">\n'
        f'    <div class="r-hdr-left">{logo_html}{dekra_html}</div>\n'
        f'    {am_html}\n'
        '  </div>\n'
        '  <div class="r-subhdr"><span class="r-subhdr-title">Certificat d’aptitude à la conduite en sécurité</span></div>\n'
        '  <div class="r-body">\n'
        '    <div class="r-left">\n'
        f'      <span class="r-fam-badge">{fam_badge}</span>\n'
        f'      {nums_html}\n'
        f'      <div class="r-titulaire">{_esc(s.nom)} {_esc(s.prenom)}</div>\n'
        f'      {ddn_recto}\n'
        '      <div class="r-spacer"></div>\n'
        f'      {org_html}\n'
        f'      {siret_html}\n'
        f'      {sign_bloc}\n'
        '    </div>\n'
        '    <div class="r-right">\n'
        f'      {photo_html}\n'
        '      <div class="r-sep"></div>\n'
        f'      {qr_html}\n'
        '      <div class="r-qr-text">Scanner · Vérifier</div>\n'
        '    </div>\n'
        '  </div>\n'
        '  <div class="r-ftr">La marque CACES® est protégée (INPI n° 03.3237295) · Document recto/verso obligatoire</div>\n'
        '</div>\n'
        '<div class="page">\n'
        '  <div class="v-hdr">\n'
        '    <div class="v-hdr-info">\n'
        f'      <div class="v-htitle">CACES® {_esc(carte.famille)} — {_esc(s.nom)} {_esc(s.prenom)}{ddn_verso}</div>\n'
        f'      <div class="v-hcarte">N° {_esc(carte.numero_carte)}{edition_html}</div>\n'
        '    </div>\n'
        f'    {logo2_html}\n'
        '  </div>\n'
        f'  {verso_notices_html}\n'
        '  <div class="v-tbl">\n'
        '    <table>\n'
        '      <thead><tr>'
        '<th>Famille</th><th>Cat.</th><th>Opt.</th><th>N° CACES®</th>'
        '<th>Obtention</th><th>Validité</th><th>Libellé</th>'
        '</tr></thead>\n'
        f'      <tbody>{verso_rows}</tbody>\n'
        '    </table>\n'
        '  </div>\n'
        f'  <div class="v-ftr">{verif_html}Document recto/verso. Toute copie doit comporter les 2 faces.</div>\n'
        '</div>\n'
        '</body></html>'
    )


def _html_to_pdf(html: str) -> bytes:
    """Convertit le HTML CR80 en PDF via WeasyPrint."""
    from weasyprint import HTML
    from io import BytesIO as _BIO
    buf = _BIO()
    HTML(string=html, base_url='.').write_pdf(buf)
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
    cfg = db.query(ConfigOrganisme).first() or ConfigOrganisme()
    caces_list = json.loads(carte.caces_json) if carte.caces_json else []
    verify_url = _build_verify_url(cfg, carte.numero_carte)
    fam_obj = db.query(Famille).filter(Famille.code == carte.famille).first()
    famille_libelle = fam_obj.libelle if fam_obj else ""
    doc_cert = db.query(DocumentOfficiel).filter(DocumentOfficiel.type == "certificat_organisme").first()
    numero_certificat = doc_cert.numero_certificat or "" if doc_cert else ""
    html = _render_cr80_html(carte, s, cfg, caces_list, verify_url, famille_libelle, numero_certificat)
    pdf_bytes = _html_to_pdf(html)
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
