// Conversion d'un horodatage UTC (ISO ou "YYYY-MM-DD HH:MM:SS") en heure de Paris.
// Gere automatiquement ete/hiver via Intl. Usage :
//   tzParis("2026-07-03T14:42:00Z")            -> "03/07/2026 16:42"
//   tzParis("2026-07-03T14:42:00Z", true)      -> "16:42"
(function () {
  function _parse(v) {
    if (v == null) return null;
    if (v instanceof Date) return v;
    var s = String(v).trim();
    // Si pas de fuseau explicite, on suppose UTC (cas du back : utcnow).
    if (/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(s) && !/[zZ]|[+\-]\d{2}:?\d{2}$/.test(s)) {
      s = s.replace(" ", "T") + "Z";
    }
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }
  window.tzParis = function (v, heureSeule) {
    var d = _parse(v);
    if (!d) return "";
    var opts = heureSeule
      ? { timeZone: "Europe/Paris", hour: "2-digit", minute: "2-digit" }
      : { timeZone: "Europe/Paris", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" };
    return new Intl.DateTimeFormat("fr-FR", opts).format(d);
  };
})();
