from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FamilyTemplate:
    family: str
    doc_id: str
    title: str
    source: str
    provisional: bool = False


DEFAULT_FAMILY_TEMPLATES = {
    "ordinary_time": FamilyTemplate(
        family="ordinary_time",
        doc_id="1WGz_KrwINqhGuJWohKjw0hluX4LzeMOFi5DlBpy0BAs",
        title="Ordinary Time Template",
        source="Drive template doc",
    ),
    "advent": FamilyTemplate(
        family="advent",
        doc_id="1rmHn0dnjVQihDz5PXMHPaoKYnvruPrWdoR1Iw2FeNic",
        title="Advent Template",
        source="Drive template doc",
    ),
    "epiphany": FamilyTemplate(
        family="epiphany",
        doc_id="12KXw2sLuYVHbcAp8os8DZdGMY9_iZL90xgMaA4k7lkk",
        title="Epiphany Template",
        source="Drive template doc",
    ),
    "lent": FamilyTemplate(
        family="lent",
        doc_id="1YbgN50TTdCnkc2HQUwm0ho-y1DkpF3T5kAh_sGXFKio",
        title="Lent Template",
        source="Drive template doc",
    ),
    "easter": FamilyTemplate(
        family="easter",
        doc_id="1NSJwogxgqUXDXdhec5dQcmP2gPBqqx6c-pW1Hzkv9qw",
        title="Easter Template",
        source="Drive template doc",
    ),
    "ash_wednesday": FamilyTemplate(
        family="ash_wednesday",
        doc_id="1lC4c-NFFdQkcT6RSpTZvPWBy6FBesQgCeYxwJfkrnao",
        title="Ash Wednesday Evening (template)",
        source="Drive template doc",
    ),
    "palm_sunday": FamilyTemplate(
        family="palm_sunday",
        doc_id="1bOjQ-xiYkfrYFUEQpj0QCO7H-7O6HcTew0n58TAR0ko",
        title="Palm Sunday 3/29/2026",
        source="Most recent live doc",
        provisional=True,
    ),
    "christmas": FamilyTemplate(
        family="christmas",
        doc_id="1Soj-vXb1K9nQDbgO7ew1qN0A-MfKVAK3ohUhLiozOcM",
        title="Christmas 2, 1/4/26",
        source="Most recent live doc",
        provisional=True,
    ),
    "pentecost": FamilyTemplate(
        family="pentecost",
        doc_id="1w5bub19Awm4noQV_rZ7Zdf6e8mCL8QacjiSbH2wd8w0",
        title="Pentecost 6/8/2025",
        source="Most recent live doc",
        provisional=True,
    ),
}


def get_family_template(family: str) -> FamilyTemplate:
    if family not in DEFAULT_FAMILY_TEMPLATES:
        raise KeyError(f"No family template configured for: {family}")
    return DEFAULT_FAMILY_TEMPLATES[family]
