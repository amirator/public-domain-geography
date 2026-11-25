"""Public-domain status engine, as of 1 January 2026.

Each country function returns a Cell: status ('PD', 'Protected', 'Uncertain'),
pd_year (first full calendar year the work is free under the main reading;
None when unknown), alt_year (the competing reading for Uncertain cells),
and a short note naming the rule applied. Sources for every rule are in
data/country_rules.csv. This models the *underlying work* (text, score,
painting, film) - not translations, editions, recordings, restorations,
trademarks or moral rights. It is a research model, not legal advice.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

AS_OF = 2026  # status on 1 January 2026

EU = {"FR", "DE", "ES", "AT", "BE", "NL", "FI", "IE", "IT", "DK", "SE", "PT", "CZ"}
EEA = EU | {"NO", "IS", "LI"}
ALLIED_3794 = {"US", "GB", "FR", "CA", "AU", "NZ"}  # Japan wartime extension, 3,794 days
COUNTRIES = ["GB", "FR", "DE", "ES", "US", "CA", "MX", "BR", "CO",
             "JP", "CN", "KR", "AU", "NZ", "ZA", "NG", "EG", "RU"]
NAMES = {"GB": "United Kingdom", "FR": "France", "DE": "Germany", "ES": "Spain", "US": "United States",
         "CA": "Canada", "MX": "Mexico", "BR": "Brazil", "CO": "Colombia", "JP": "Japan", "CN": "China",
         "KR": "South Korea", "AU": "Australia", "NZ": "New Zealand", "ZA": "South Africa", "NG": "Nigeria",
         "EG": "Egypt", "RU": "Russia"}


@dataclass
class Cell:
    status: str
    pd_year: int | None
    alt_year: int | None = None
    note: str = ""


@dataclass
class Work:
    id: str
    title: str
    type: str
    death: int          # last relevant author's death year (Wikidata)
    pub_year: int
    origin: str
    author_nat: str
    flags: frozenset = frozenset()


def life_plus(death: int, n: int) -> int:
    """Terms run to the end of the calendar year; work is free on 1 Jan of the returned year."""
    return death + n + 1


def _status(year: int | None) -> str:
    if year is None:
        return "Uncertain"
    return "PD" if year <= AS_OF else "Protected"


def _mk(year: int | None, note: str) -> Cell:
    return Cell(_status(year), year, None, note)


def _uncertain(main: int | None, alt: int | None, note: str) -> Cell:
    """Two defensible readings. If both agree on today's status, keep the main status."""
    if main is not None and alt is not None and _status(main) == _status(alt):
        return Cell(_status(main), main, alt, note)
    return Cell("Uncertain", main, alt, note)


# ---------- origin-country term (used for the rule of the shorter term and URAA) ----------

def origin_pd_year(w: Work) -> int | None:
    o = "RU" if w.origin == "SU" else w.origin
    if o in COUNTRIES:
        return COUNTRY_FN[o](w, shorter_term=False).pd_year
    if o in EEA or o in {"CL", "AR"}:  # life + 70 (EU/EEA directive; Chile Ley 17.336 art. 10; Argentina Ley 11.723 art. 5)
        return life_plus(w.death, 70)
    return None


def _shorter_term(w: Work, local: Cell, country: str, exempt: set[str]) -> Cell:
    """Comparison of terms: if the work's origin is foreign (and outside `exempt`) and the author
    is not a national of an exempt country, protection may be capped at the origin-country term."""
    if w.origin in exempt or w.origin == country or w.author_nat in exempt or local.status == "PD":
        return local
    o = origin_pd_year(w)
    if o is None or local.pd_year is None or o >= local.pd_year:
        return local
    if o <= AS_OF:
        return Cell("Uncertain", local.pd_year, o,
                    local.note + f"; rule of the shorter term would cap protection at the origin-country term (free {o})")
    return Cell(local.status, o, local.pd_year, local.note + f"; capped by origin-country term (free {o})")


# ---------- countries ----------

def gb(w: Work, shorter_term: bool = True) -> Cell:
    c = _mk(life_plus(w.death, 70), "CDPA 1988 s.12 / s.13B (films): life + 70")
    if "uk_peter_pan" in w.flags:
        c.note += "; perpetual royalty to Great Ormond Street Hospital (CDPA s.301, Sch.6)"
    return _shorter_term(w, c, "GB", EEA | {"GB"}) if shorter_term else c


def _eu(w: Work, country: str, shorter_term: bool) -> Cell:
    c = _mk(life_plus(w.death, 70), "Directive 2006/116/EC art.1-2: life + 70 (films: last of director, screenwriter, dialogue author, composer)")
    return _shorter_term(w, c, country, EEA) if shorter_term else c


def fr(w: Work, shorter_term: bool = True) -> Cell:
    if w.id == "m01":  # Boléro: verified date
        return Cell("PD", 2016, None, "CPI L123-1 + L123-9 wartime extension (8 y 120 d): free 1 May 2016")
    if "mort_pour_la_france" in w.flags:
        return Cell("Protected", 2032, None, "CPI L123-10 'mort pour la France' +30 y and L123-9 wartime extension: free 2032")
    c = _eu(w, "FR", shorter_term)
    if w.type == "music" and w.pub_year <= 1947 and 1937 < w.death < 1995:
        ext_days = 8 * 365 + 120 + (6 * 365 + 152 if w.pub_year <= 1919 else 0)
        alt = math.ceil(life_plus(w.death, 70) + ext_days / 365.25)
        return _uncertain(c.pd_year, alt, c.note + "; French wartime extensions (CPI L123-8/9) may extend musical works")
    return c


def de(w: Work, shorter_term: bool = True) -> Cell:
    c = _eu(w, "DE", shorter_term)
    if w.origin == "US" and c.status == "Uncertain":
        c.note += " (BGH I ZR 49/13 'Tarzan', 2014, applied the shorter US term via the UCC)"
    return c


def es(w: Work, shorter_term: bool = True) -> Cell:
    if w.death < 1987:
        if w.author_nat == "ES":
            return _mk(life_plus(w.death, 80), "LPI 1996 Disposición transitoria 4ª: authors who died before 7 Dec 1987 get life + 80")
        base = _eu(w, "ES", shorter_term)
        if base.status == "Uncertain":
            return base
        if w.author_nat in EEA | {"GB"}:
            return _uncertain(base.pd_year, life_plus(w.death, 80),
                              base.note + "; Spain's life+80 transitional term (DT 4ª LPI) may extend to authors who were EU nationals (UK authors until 2020)")
        return base
    return _eu(w, "ES", shorter_term)


def us(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "art":
        if w.pub_year <= 1930 and w.death <= 1955:
            return _mk(min(w.pub_year + 96, life_plus(w.death, 70)), "17 USC 303/304: free whether treated as published (pre-1931) or unpublished (life + 70)")
        if w.pub_year <= 1930:
            return _uncertain(w.pub_year + 96, life_plus(w.death, 70),
                              "Depends on whether the artwork counts as 'published' before 1931 (free) or unpublished (life + 70)")
        return _uncertain(w.pub_year + 96, life_plus(w.death, 70),
                          "Publication status of the artwork decides 95-years-from-publication vs life + 70")
    if w.pub_year <= 1930:
        return _mk(w.pub_year + 96, "17 USC 304: works published 1930 or earlier are free (Duke CSPD, Public Domain Day 2026)")
    if w.pub_year <= 1977:
        yr = w.pub_year + 96
        if w.origin == "US":
            note = "17 USC 304: 95 years from publication (assumes copyright was renewed)"
            if "us_renewal_unknown" in w.flags:
                return _uncertain(yr, None, note + "; renewal not verified")
            return Cell("Protected", yr, None, note)
        o = origin_pd_year(w)
        if (o is not None and o > 1996) or (o is None and w.pub_year >= 1946):
            note = "17 USC 104A (URAA): foreign work restored for 95 years from publication"
            if "us_renewal_unknown" in w.flags:
                return _uncertain(yr, None, note + "; possible simultaneous US publication makes renewal relevant")
            return Cell("Protected", yr, None, note)
        return _uncertain(yr, None, "Foreign work possibly not eligible for URAA restoration (origin term may have ended before 1996)")
    return _mk(life_plus(w.death, 70), "17 USC 302: life + 70")


def ca(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Film term not modelled for Canada")
    if w.death <= 1971:
        return _mk(life_plus(w.death, 50), "Copyright Act s.6: life + 50 (authors died 1971 or earlier; 2022 extension not retroactive)")
    return _mk(life_plus(w.death, 70), "Copyright Act s.6 as amended 30 Dec 2022: life + 70")


def mx(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Film term not modelled for Mexico")
    if w.death <= 1951:
        return Cell("PD", None, None, "Term expired before the non-retroactive 1982 extension (authors died before 1952)")
    return _mk(life_plus(w.death, 100), "LFDA art. 29 (2003): life + 100; extensions of 1982/1994/2003 applied to works still protected")


def br(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return _mk(w.pub_year + 71, "Lei 9.610/1998 art. 44: films 70 years from 1 Jan after release")
    return _mk(life_plus(w.death, 70), "Lei 9.610/1998 art. 41: life + 70")


def co(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Film term not modelled for Colombia")
    return _mk(life_plus(w.death, 80), "Ley 23 de 1982 art. 11: life + 80")


def jp(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Japanese film terms (old-law life-based vs 70 from release) not modelled")
    base = life_plus(w.death, 50) if w.death <= 1967 else life_plus(w.death, 70)
    note = "Copyright Act art. 51: life + 70 since 30 Dec 2018, not retroactive (authors died 1967 or earlier: life + 50)"
    c = _mk(base, note)
    if w.author_nat in ALLIED_3794 and w.pub_year <= 1951:
        days = 3794 if w.pub_year <= 1941 else max(0, (1952 - w.pub_year) * 365)
        alt = math.ceil(base + days / 365.25)
        c = _uncertain(base, alt, note + "; wartime extension for Allied nationals (Act No. 302 of 1952) adds up to 3,794 days")
    if shorter_term:
        c = _shorter_term(w, c, "JP", {"JP"})
    return c


def cn(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return _mk(w.pub_year + 51, "Copyright Law art. 23 (2020): audiovisual works 50 years from first publication")
    return _mk(life_plus(w.death, 50), "Copyright Law art. 23 (2020): life + 50")


def kr(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Film term not modelled for South Korea")
    if w.death <= 1962:
        return _mk(life_plus(w.death, 50), "Copyright Act art. 39: life + 70 from 1 July 2013, not retroactive (authors died 1962 or earlier already free)")
    return _mk(life_plus(w.death, 70), "Copyright Act art. 39: life + 70")


def au(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Film term not modelled for Australia")
    if w.death <= 1954:
        return _mk(life_plus(w.death, 50), "Copyright Act 1968 s.33: authors died before 1955 are free (2005 extension not retroactive)")
    return _mk(life_plus(w.death, 70), "Copyright Act 1968 s.33: life + 70")


def nz(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return _mk(w.pub_year + 51, "Copyright Act 1994 s.23: films 50 years from making / release")
    return _mk(life_plus(w.death, 50), "Copyright Act 1994 s.22: life + 50")


def za(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return _mk(w.pub_year + 51, "Copyright Act 98 of 1978 s.3(2)(b): films 50 years from release")
    return _mk(life_plus(w.death, 50), "Copyright Act 98 of 1978 s.3(2)(a): life + 50")


def ng(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Film term not modelled for Nigeria")
    return _mk(life_plus(w.death, 70), "Copyright Act 2022 s.19: life + 70")


def eg(w: Work, shorter_term: bool = True) -> Cell:
    if w.type == "film":
        return Cell("Not modelled", None, None, "Film term not modelled for Egypt")
    return _mk(life_plus(w.death, 50), "Law 82/2002 art. 160: life + 50")


def ru(w: Work, shorter_term: bool = True) -> Cell:
    if w.death <= 1942:
        return _mk(life_plus(w.death, 50), "Rights that expired (life + 50) before 1 Jan 1993 are not revived (Federal Law 231-FZ, art. 6)")
    c = _mk(life_plus(w.death, 70), "Civil Code art. 1281 (films: art. 1263 authors): life + 70")
    if "ru_war_worker" in w.flags:
        c = _uncertain(c.pd_year, life_plus(w.death, 74), c.note + "; +4 years if the author worked during the Great Patriotic War (art. 1281(5))")
    if shorter_term:
        c = _shorter_term(w, c, "RU", {"RU", "SU"})
    return c


COUNTRY_FN = {"GB": gb, "FR": fr, "DE": de, "ES": es, "US": us, "CA": ca, "MX": mx, "BR": br, "CO": co,
              "JP": jp, "CN": cn, "KR": kr, "AU": au, "NZ": nz, "ZA": za, "NG": ng, "EG": eg, "RU": ru}


SHORTER_TERM_MODELLED = {"GB", "FR", "DE", "ES", "JP", "RU", "US"}  # US: no comparison of terms


def cell(w: Work, country: str) -> Cell:
    c = COUNTRY_FN[country](w)
    origin = "RU" if w.origin == "SU" else w.origin
    if country not in SHORTER_TERM_MODELLED and c.status == "Protected" and origin != country:
        o = origin_pd_year(w)
        if o is not None and o <= AS_OF < (c.pd_year or 0):
            return Cell("Uncertain", c.pd_year, o, c.note + f"; free in the origin country since {o} - whether this "
                        "country applies the Berne art. 7(8) comparison of terms was not verified")
    return c
