from __future__ import annotations

import unittest
from datetime import date

from booklet.reference_resolver import resolve_sunday_reference
from booklet.request_router import _infer_action, _parse_request_parts
from booklet.pco_pdf_publish import build_pdf_filename


class BookletRoutingTests(unittest.TestCase):
    def test_next_week_resolves_to_next_sunday(self) -> None:
        resolution = resolve_sunday_reference(
            "what songs are we singing next week",
            today=date(2026, 3, 30),
        )
        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.resolved.service_date.isoformat(), "2026-04-05")

    def test_ordinary_time_phrase_is_ambiguous(self) -> None:
        resolution = resolve_sunday_reference(
            "make a liturgy leader guide for the third Sunday of ordinary time",
            today=date(2026, 3, 30),
        )
        self.assertEqual(resolution.status, "ambiguous")
        self.assertEqual(
            [candidate.service_date.isoformat() for candidate in resolution.candidates],
            ["2026-01-25", "2026-06-14"],
        )

    def test_month_day_phrase_resolves(self) -> None:
        resolution = resolve_sunday_reference(
            "send me the June 14 liturgy link",
            today=date(2026, 3, 30),
        )
        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.resolved.service_date.isoformat(), "2026-06-14")

    def test_named_sunday_embedded_in_sentence_resolves(self) -> None:
        resolution = resolve_sunday_reference(
            "update the Trinity Sunday booklet",
            today=date(2026, 3, 30),
        )
        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.resolved.service_date.isoformat(), "2026-05-31")

    def test_infer_make_action(self) -> None:
        self.assertEqual(
            _infer_action("make a liturgy leader guide for June 14"),
            "make",
        )

    def test_infer_link_action(self) -> None:
        self.assertEqual(
            _infer_action("send me the link for June 14"),
            "link",
        )

    def test_infer_songs_action(self) -> None:
        self.assertEqual(
            _infer_action("what songs are we singing next week"),
            "songs",
        )

    def test_infer_roles_action(self) -> None:
        self.assertEqual(
            _infer_action("who is serving this sunday"),
            "roles",
        )

    def test_infer_attach_action(self) -> None:
        self.assertEqual(
            _infer_action("upload the liturgy PDF to Planning Center for Trinity Sunday"),
            "attach",
        )

    def test_infer_make_attach_action(self) -> None:
        self.assertEqual(
            _infer_action("make the Trinity Sunday booklet and upload the PDF to Planning Center"),
            "make_attach",
        )

    def test_parse_explicit_action(self) -> None:
        action, query = _parse_request_parts(["update", "Proper", "6"])
        self.assertEqual(action, "update")
        self.assertEqual(query, "Proper 6")

    def test_build_pdf_filename(self) -> None:
        self.assertEqual(
            build_pdf_filename("Trinity Sunday", "2026-05-31"),
            "Trinity Sunday.pdf",
        )


if __name__ == "__main__":
    unittest.main()
