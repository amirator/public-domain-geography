"""Regression tests: each case is a fact verified against a published source."""
import pandas as pd
import pytest

from src.build_matrix import build

M = build().set_index(["title", "country"])


def get(title, country):
    r = M.loc[(title, country)]
    return r["status"], (None if pd.isna(r["pd_year"]) else int(r["pd_year"]))


@pytest.mark.parametrize("title,country,status,year", [
    ("Nineteen Eighty-Four", "GB", "PD", 2021),        # Guardian, 1 Jan 2021
    ("Nineteen Eighty-Four", "US", "Protected", 2045),  # free in US on 1 Jan 2045
    ("The Hobbit", "NZ", "PD", 2024),                    # NZ s.22 life+50; Stuff, Jan 2024
    ("The Little Prince", "FR", "Protected", 2032),     # franceinfo 2015: 2032 in France
    ("The Little Prince", "DE", "PD", 2015),             # EU 2015
    ("The Little Prince", "CA", "PD", 1995),             # franceinfo: Canada 1995
    ("Boléro", "FR", "PD", 2016),                        # France Musique: 1 May 2016
    ("Metropolis (1927)", "US", "PD", 2023),
    ("Metropolis (1927)", "DE", "Protected", 2047),      # Lang d.1976 -> through 2046
    ("Les Demoiselles d'Avignon", "ES", "Protected", 2054),  # BNE: Picasso free in Spain 2054
    ("Winnie-the-Pooh (text)", "GB", "Protected", 2027),
    ("Winnie-the-Pooh (text)", "US", "PD", 2022),
    ("Tintin in the Land of the Soviets", "US", "PD", 2025),  # Duke CSPD 2025
    ("The Two Fridas", "MX", "Protected", 2055),
    ("The Maltese Falcon", "US", "PD", 2026),           # 1930 works free in 2026
])
def test_verified_cases(title, country, status, year):
    assert get(title, country) == (status, year)


def test_matrix_shape():
    assert M.index.get_level_values(0).nunique() >= 60
    assert M.index.get_level_values(1).nunique() >= 15


def test_every_cell_has_rule():
    assert M["rule"].str.len().min() > 10
