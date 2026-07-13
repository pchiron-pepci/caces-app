def fam_variantes(f):
    """Retourne les variantes de format d'un code famille (R.482 et R482)
    pour absorber l'incoherence historique avec/sans point."""
    f = f or ""
    sans = f.replace(".", "")
    if "." in f:
        avec = f
    elif len(f) > 1 and f[0].upper() == "R":
        avec = f[:1] + "." + f[1:]
    else:
        avec = f
    return list({f, sans, avec})
