import os
import uuid
import boto3
from botocore.config import Config

# Tenant courant — en dur pour le pilote mono-tenant.
# Migrable au control plane a l'arrivee d'un second client.
TENANT = "pepci"

# Extensions et types MIME autorises pour les justificatifs
EXTENSIONS_AUTORISEES = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "heic"}
MIME_AUTORISES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
    "image/heic",
}
TAILLE_MAX = 10 * 1024 * 1024  # 10 Mo

def _client():
    """Client S3 pointe sur l'endpoint R2. Lit les variables d'environnement a chaque appel."""
    endpoint = os.getenv("R2_ENDPOINT")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    if not (endpoint and access_key and secret_key):
        raise RuntimeError("Variables R2 manquantes (R2_ENDPOINT / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY).")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

def _bucket():
    b = os.getenv("R2_BUCKET")
    if not b:
        raise RuntimeError("Variable R2_BUCKET manquante.")
    return b

def construire_cle(prefixe: str, nom_fichier: str) -> str:
    """Genere une cle objet unique : {tenant}/{prefixe}/{uuid}.{ext}"""
    ext = ""
    if "." in nom_fichier:
        ext = nom_fichier.rsplit(".", 1)[1].lower()
    suffixe = f".{ext}" if ext else ""
    return f"{TENANT}/{prefixe}/{uuid.uuid4().hex}{suffixe}"

def upload_fichier(contenu: bytes, cle: str, content_type: str) -> None:
    """Envoie un binaire vers R2 sous la cle donnee."""
    _client().put_object(
        Bucket=_bucket(),
        Key=cle,
        Body=contenu,
        ContentType=content_type or "application/octet-stream",
    )

def get_fichier(cle: str) -> bytes:
    """Recupere le binaire depuis R2."""
    reponse = _client().get_object(Bucket=_bucket(), Key=cle)
    return reponse["Body"].read()

def delete_fichier(cle: str) -> None:
    """Supprime l'objet de R2. Silencieux si la cle n'existe pas."""
    _client().delete_object(Bucket=_bucket(), Key=cle)

def generer_url_presignee(cle: str, nom_telechargement: str = None, inline: bool = False, expire: int = 3600) -> str:
    """URL temporaire signee vers un objet R2, sans exposer les cles d'acces.
    inline=True : affichage navigateur ; inline=False : telechargement. expire en secondes."""
    params = {"Bucket": _bucket(), "Key": cle}
    disposition = "inline" if inline else "attachment"
    if nom_telechargement:
        params["ResponseContentDisposition"] = f'{disposition}; filename="{nom_telechargement}"'
    return _client().generate_presigned_url("get_object", Params=params, ExpiresIn=expire)

def test_connexion() -> dict:
    """Teste la connexion R2 : ecrit un petit objet, le relit, le supprime."""
    cle = construire_cle("_selftest", "test.txt")
    try:
        upload_fichier(b"noryx-r2-ok", cle, "text/plain")
        relu = get_fichier(cle)
        delete_fichier(cle)
        return {"ok": relu == b"noryx-r2-ok", "cle_testee": cle}
    except Exception as e:
        return {"ok": False, "erreur": str(e)}
