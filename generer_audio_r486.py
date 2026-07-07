"""
generer_audio_r486.py
Genere les MP3 des questions theoriques R.486 avec Amazon Polly (neural, eu-west-3).
Double voix : _H (Remi, masculine) et _F (Lea, feminine).
Textes lus depuis init_questions_r486.py (dict GRILLES_R486), SSML genere par regex.
Nommage : R486_G{grille}_T{theme}_Q{numero}_{H|F}.mp3
Echantillons d'intro : R486_ECHANTILLON_{H|F}.mp3

USAGE (dans un environnement avec credentials AWS, ex. CloudShell) :
  pip3 install boto3
  python3 generer_audio_r486.py                 -> 1000 MP3 (H+F) + 2 echantillons
  python3 generer_audio_r486.py H               -> voix homme uniquement
  python3 generer_audio_r486.py F --force       -> regenere voix femme
  python3 generer_audio_r486.py G1 T3 Q47 F --force  -> une question, voix femme
"""
import os, re, sys, ast, html, boto3

_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "init_questions_r486.py"), encoding="utf-8").read()
_tree = ast.parse(_src)
GRILLES_R486 = None
for _node in _tree.body:
    if isinstance(_node, ast.Assign):
        for _t in _node.targets:
            if isinstance(_t, ast.Name) and _t.id == "GRILLES_R486":
                GRILLES_R486 = ast.literal_eval(_node.value)
if GRILLES_R486 is None:
    print("[ERREUR] GRILLES_R486 introuvable"); sys.exit(1)

RATE = "95%"
REGION = "eu-west-3"
VOIX = {"H": "Remi", "F": "Lea"}

SIGLES_EPELES = ["PEMP", "EPI", "VGP", "GPL", "ROPS", "FOPS", "SMS", "CE", "AIPR"]

NETTOYAGE = [
    (r"\[(\d+)\]", r"repere \1"),
    (r"\[Carsat/Cramif/CGSS\]\*?", "Carsat"),
    (r"\bCMU\b", "charge maximale d'utilisation"),
    (r"\bclasse\s+II\b", "classe 2"),
    (r"(\d+)\s*N\b", r"\1 Newton"),
    (r"®", ""),
    (r"\bCACES\b", "quacèsse"),
    (r"[\"«»]", ""),
    (r"\bkm/h\b", "kilometre heure"),
    (r"\bkV\b", "kilovolts"),
    (r"\bV\b", "volts"),
    (r"\s{2,}", " "),
]

SPELL = '<say-as interpret-as="spell-out">%s</say-as>'

def epeler_lettres_categorie(t):
    t = re.sub(r"(cat[ée]gorie\s+)([ABC])\b", lambda m: m.group(1) + (SPELL % m.group(2)), t, flags=re.IGNORECASE)
    t = re.sub(r"(groupe\s+)([ABC])\b", lambda m: m.group(1) + (SPELL % m.group(2)), t, flags=re.IGNORECASE)
    t = re.sub(r"(type\s+)([13])([AB])\b", lambda m: m.group(1) + m.group(2) + " " + (SPELL % m.group(3)), t, flags=re.IGNORECASE)
    t = re.sub(r"\b([13])([AB])\b", lambda m: m.group(1) + " " + (SPELL % m.group(2)), t)
    return t

def construire_ssml(texte):
    t = texte
    for motif, repl in NETTOYAGE:
        t = re.sub(motif, repl, t)
    t = t.strip()
    t = html.escape(t)
    for sig in SIGLES_EPELES:
        t = re.sub(r"\b" + sig + r"\b", SPELL % sig, t)
    t = epeler_lettres_categorie(t)
    return '<speak><prosody rate="%s">%s</prosody></speak>' % (RATE, t)

def synth(client, ssml, voice_id, chemin):
    resp = client.synthesize_speech(
        Text=ssml, TextType="ssml", OutputFormat="mp3",
        VoiceId=voice_id, Engine="neural", LanguageCode="fr-FR")
    with open(chemin, "wb") as f:
        f.write(resp["AudioStream"].read())

def main():
    args = list(sys.argv[1:])
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    fg = ft = fq = None
    fvoix = None
    for a in args:
        if re.fullmatch(r"G\d+", a): fg = int(a[1:])
        elif re.fullmatch(r"T\d+", a): ft = int(a[1:])
        elif re.fullmatch(r"Q\d+", a): fq = int(a[1:])
        elif a in ("H", "F"): fvoix = a
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_r486")
    os.makedirs(out_dir, exist_ok=True)
    client = boto3.client("polly", region_name=REGION)

    voix_a_faire = [fvoix] if fvoix else ["H", "F"]

    phrase_intro = "Bonjour, cette voix lira les questions de votre epreuve theorique. Si vous preferez cette voix, selectionnez-la."
    ssml_intro = '<speak><prosody rate="%s">%s</prosody></speak>' % (RATE, html.escape(phrase_intro))
    for v in voix_a_faire:
        nom = "R486_ECHANTILLON_%s.mp3" % v
        chemin = os.path.join(out_dir, nom)
        if not (os.path.exists(chemin) and not force):
            synth(client, ssml_intro, VOIX[v], chemin)
            print("[OK] %s" % nom)

    genere = saute = 0
    for gnum, themes in GRILLES_R486.items():
        if fg and gnum != fg: continue
        for tnum, questions in themes.items():
            if ft and tnum != ft: continue
            for (qnum, texte, _r) in questions:
                if fq and qnum != fq: continue
                ssml = construire_ssml(texte)
                for v in voix_a_faire:
                    nom = "R486_G%d_T%d_Q%d_%s.mp3" % (gnum, tnum, qnum, v)
                    chemin = os.path.join(out_dir, nom)
                    if os.path.exists(chemin) and not force:
                        saute += 1
                        continue
                    synth(client, ssml, VOIX[v], chemin)
                    genere += 1
                    print("[OK] %s" % nom)
    print("\n%d MP3 generes, %d ignores. Dossier: %s" % (genere, saute, out_dir))

if __name__ == "__main__":
    main()
