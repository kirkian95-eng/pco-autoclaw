#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date

from booklet.assembler import assemble_service
from booklet.config import load_config
from booklet.corpus_analysis import write_corpus_rules_report
from booklet.document_renderer import build_render_plan
from booklet.example_analysis import write_example_analysis_report
from booklet.template_profiles import build_template_profile, render_template_profile_markdown
from booklet.manifest import (
    get_planned_service,
    init_manifest,
    list_planned_services,
    mark_generated_service,
    upsert_planned_service,
)
from booklet.master_templates import get_family_template
from booklet.models import PlannedService
from booklet.pco_pdf_publish import attach_booklet_pdf
from booklet.planner import build_planned_service


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    config = load_config()

    if args.command == "init-manifest":
        init_manifest(config.manifest_db)
        print(f"Initialized manifest: {config.manifest_db}")
        return 0

    if args.command == "show-config":
        print(
            json.dumps(
                {
                    "manifest_db": str(config.manifest_db),
                    "default_service_type_id": config.default_service_type_id,
                    "planning_workbook_file": str(config.planning_workbook_file),
                    "google_service_account_file": str(config.google_service_account_file)
                    if config.google_service_account_file
                    else None,
                    "google_oauth_client_secret_file": str(config.google_oauth_client_secret_file)
                    if config.google_oauth_client_secret_file
                    else None,
                    "google_oauth_token_file": str(config.google_oauth_token_file)
                    if config.google_oauth_token_file
                    else None,
                    "google_template_root_id": config.google_template_root_id,
                    "google_output_root_id": config.google_output_root_id,
                    "ordinary_template_doc_id": config.ordinary_template_doc_id,
                    "missing_for_generation": config.missing_for_generation(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "plan":
        init_manifest(config.manifest_db)
        planned = build_planned_service(
            service_date=date.fromisoformat(args.date),
            service_type_id=args.service_type_id or config.default_service_type_id,
            template_family=args.template_family,
        )
        doc_id = upsert_planned_service(config.manifest_db, planned)
        print(
            json.dumps(
                {
                    "document_id": doc_id,
                    "planned_service": planned.to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "list-plans":
        init_manifest(config.manifest_db)
        print(json.dumps(list_planned_services(config.manifest_db), indent=2, sort_keys=True))
        return 0

    if args.command == "preview-service":
        assembled = assemble_service(
            config=config,
            service_date=date.fromisoformat(args.date),
            service_type_id=args.service_type_id or config.default_service_type_id,
            template_family=args.template_family,
            include_pco=not args.skip_pco,
            include_scripture=not args.skip_scripture,
        )
        print(json.dumps(assembled.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "analyze-examples":
        output_path = write_example_analysis_report(config, args.output)
        print(
            json.dumps(
                {
                    "output_path": str(output_path),
                    "status": "ok",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "analyze-corpus":
        output_path = write_corpus_rules_report(config, args.output)
        print(
            json.dumps(
                {
                    "output_path": str(output_path),
                    "status": "ok",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "inspect-template":
        profile = build_template_profile(config, args.family)
        print(json.dumps(profile.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "render-template-profile":
        output = render_template_profile_markdown(config, args.family)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
            print(
                json.dumps(
                    {
                        "output_path": str(args.output),
                        "status": "ok",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(output)
        return 0

    if args.command == "auth-google":
        from booklet.sources.google_docs import start_oauth_console_flow

        auth_url, state = start_oauth_console_flow(config)
        print(
            json.dumps(
                {
                    "auth_url": auth_url,
                    "state": state,
                    "status": "authorization_required",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "auth-google-finish":
        from booklet.sources.google_docs import finish_oauth_console_flow

        token_path = finish_oauth_console_flow(
            config,
            auth_code=args.code,
            state=args.state,
            response_url=args.response_url,
        )
        print(
            json.dumps(
                {
                    "token_file": str(token_path),
                    "status": "authorized",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "copy-template":
        from booklet.sources.google_docs import GoogleDocsClient

        client = GoogleDocsClient(config)
        source_doc_id = args.doc_id or _default_source_doc_id(config, args.template_family)
        if not config.google_output_root_id:
            parser.error("BOOKLET_GOOGLE_OUTPUT_ROOT_ID is not configured")

        new_title = args.title or _default_title(args.template_family, args.date)
        copied = client.copy_doc(
            source_doc_id=source_doc_id,
            new_title=new_title,
            parent_folder_id=config.google_output_root_id,
        )
        print(
            json.dumps(
                {
                    "source_doc_id": source_doc_id,
                    "copied_doc": {
                        "doc_id": copied.doc_id,
                        "title": copied.title,
                        "parent_id": copied.parent_id,
                        "url": f"https://docs.google.com/document/d/{copied.doc_id}/edit",
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "render-booklet-plan":
        from booklet.sources.google_docs import GoogleDocsClient

        assembled = assemble_service(
            config=config,
            service_date=date.fromisoformat(args.date),
            service_type_id=args.service_type_id or config.default_service_type_id,
            template_family=args.template_family,
            include_pco=not args.skip_pco,
            include_scripture=not args.skip_scripture,
        )
        client = GoogleDocsClient(config)
        source_doc_id = args.doc_id or _default_source_doc_id(config, args.template_family)
        plan = build_render_plan(assembled, client.get_paragraphs(source_doc_id))
        print(
            json.dumps(
                {
                    "assembled_service": assembled.to_dict(),
                    "render_plan": plan.to_dict(),
                    "source_doc_id": source_doc_id,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "generate-booklet":
        from booklet.sources.google_docs import GoogleDocsClient

        init_manifest(config.manifest_db)
        service_type_id = args.service_type_id or config.default_service_type_id
        existing = get_planned_service(
            config.manifest_db,
            service_date=args.date,
            service_type_id=service_type_id,
        )
        if existing and existing.get("doc_id") and not args.force_new:
            attachment = None
            if args.attach_pdf_to_pco:
                attachment = attach_booklet_pdf(
                    config=config,
                    service_date=existing["service_date"],
                    service_type_id=existing["service_type_id"],
                    doc_id=existing["doc_id"],
                    plan_id=existing.get("plan_id"),
                )
            print(
                json.dumps(
                    {
                        "attachment": attachment,
                        "status": "exists",
                        "doc_id": existing["doc_id"],
                        "service_date": existing["service_date"],
                        "service_type_id": existing["service_type_id"],
                        "template_family": existing["template_family"],
                        "url": f"https://docs.google.com/document/d/{existing['doc_id']}/edit",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        assembled = assemble_service(
            config=config,
            service_date=date.fromisoformat(args.date),
            service_type_id=service_type_id,
            template_family=args.template_family,
            include_pco=not args.skip_pco,
            include_scripture=not args.skip_scripture,
        )
        source_doc_id = args.doc_id or _default_source_doc_id(config, args.template_family)
        if args.dry_run:
            client = GoogleDocsClient(config)
            plan = build_render_plan(assembled, client.get_paragraphs(source_doc_id))
            print(
                json.dumps(
                    {
                        "assembled_service": assembled.to_dict(),
                        "dry_run": True,
                        "render_plan": plan.to_dict(),
                        "source_doc_id": source_doc_id,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if not config.google_output_root_id:
            parser.error("BOOKLET_GOOGLE_OUTPUT_ROOT_ID is not configured")

        client = GoogleDocsClient(config)
        planned = PlannedService(
            service_date=assembled.service_date,
            service_type_id=assembled.service_type_id,
            template_family=assembled.template_family,
            season=assembled.season,
            observance=assembled.observance,
            plan_id=assembled.plan_id,
        )
        upsert_planned_service(config.manifest_db, planned)
        copied = client.copy_doc(
            source_doc_id=source_doc_id,
            new_title=args.title or _default_title(args.template_family, args.date, assembled.observance),
            parent_folder_id=config.google_output_root_id,
        )
        plan = build_render_plan(assembled, client.get_paragraphs(copied.doc_id))
        client.apply_text_replacements(copied.doc_id, plan.replacements)
        mark_generated_service(
            config.manifest_db,
            service_date=assembled.service_date,
            service_type_id=assembled.service_type_id,
            doc_id=copied.doc_id,
            source_snapshot=assembled.to_dict(),
        )
        attachment = None
        if args.attach_pdf_to_pco:
            attachment = attach_booklet_pdf(
                config=config,
                service_date=assembled.service_date,
                service_type_id=assembled.service_type_id,
                doc_id=copied.doc_id,
                plan_id=assembled.plan_id,
            )
        print(
            json.dumps(
                {
                    "attachment": attachment,
                    "assembled_service": assembled.to_dict(),
                    "copied_doc": {
                        "doc_id": copied.doc_id,
                        "title": copied.title,
                        "parent_id": copied.parent_id,
                        "url": f"https://docs.google.com/document/d/{copied.doc_id}/edit",
                    },
                    "render_plan": plan.to_dict(),
                    "status": "generated",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "update-booklet":
        from booklet.sources.google_docs import GoogleDocsClient

        init_manifest(config.manifest_db)
        service_type_id = args.service_type_id or config.default_service_type_id
        existing = get_planned_service(
            config.manifest_db,
            service_date=args.date,
            service_type_id=service_type_id,
        )
        if not existing or not existing.get("doc_id"):
            print(
                json.dumps(
                    {
                        "status": "not_found",
                        "service_date": args.date,
                        "service_type_id": service_type_id,
                        "message": "No generated booklet exists for that Sunday. Use generate-booklet first.",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1
        template_family = args.template_family or existing["template_family"]
        assembled = assemble_service(
            config=config,
            service_date=date.fromisoformat(args.date),
            service_type_id=service_type_id,
            template_family=template_family,
            include_pco=not args.skip_pco,
            include_scripture=not args.skip_scripture,
        )
        client = GoogleDocsClient(config)
        plan = build_render_plan(assembled, client.get_paragraphs(existing["doc_id"]))
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "status": "dry_run",
                        "doc_id": existing["doc_id"],
                        "url": f"https://docs.google.com/document/d/{existing['doc_id']}/edit",
                        "assembled_service": assembled.to_dict(),
                        "render_plan": plan.to_dict(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        client.apply_text_replacements(existing["doc_id"], plan.replacements)
        mark_generated_service(
            config.manifest_db,
            service_date=assembled.service_date,
            service_type_id=assembled.service_type_id,
            doc_id=existing["doc_id"],
            source_snapshot=assembled.to_dict(),
        )
        attachment = None
        if args.attach_pdf_to_pco:
            attachment = attach_booklet_pdf(
                config=config,
                service_date=assembled.service_date,
                service_type_id=assembled.service_type_id,
                doc_id=existing["doc_id"],
                plan_id=assembled.plan_id,
            )
        print(
            json.dumps(
                {
                    "attachment": attachment,
                    "status": "updated",
                    "doc_id": existing["doc_id"],
                    "url": f"https://docs.google.com/document/d/{existing['doc_id']}/edit",
                    "render_plan": plan.to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "get-booklet-link":
        init_manifest(config.manifest_db)
        service_type_id = args.service_type_id or config.default_service_type_id
        existing = get_planned_service(
            config.manifest_db,
            service_date=args.date,
            service_type_id=service_type_id,
        )
        if not existing or not existing.get("doc_id"):
            print(
                json.dumps(
                    {
                        "status": "not_found",
                        "service_date": args.date,
                        "service_type_id": service_type_id,
                        "message": "No generated booklet link is recorded for that Sunday.",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1
        print(
            json.dumps(
                {
                    "status": "found",
                    "doc_id": existing["doc_id"],
                    "service_date": existing["service_date"],
                    "service_type_id": existing["service_type_id"],
                    "template_family": existing["template_family"],
                    "url": f"https://docs.google.com/document/d/{existing['doc_id']}/edit",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "attach-booklet-pdf":
        init_manifest(config.manifest_db)
        service_type_id = args.service_type_id or config.default_service_type_id
        attachment = attach_booklet_pdf(
            config=config,
            service_date=args.date,
            service_type_id=service_type_id,
            doc_id=args.doc_id,
            plan_id=args.plan_id,
            filename=args.filename,
        )
        print(json.dumps(attachment, indent=2, sort_keys=True))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sunday booklet generator bootstrap CLI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-manifest", help="Create the SQLite manifest schema.")
    sub.add_parser("show-config", help="Show current booklet configuration.")
    sub.add_parser("list-plans", help="List planned booklet records from SQLite.")
    sub.add_parser(
        "auth-google",
        help="Run one-time Google OAuth console flow and store a refresh token.",
    )
    auth_finish = sub.add_parser(
        "auth-google-finish",
        help="Complete Google OAuth console flow with pasted code and state.",
    )
    auth_finish.add_argument("--code", help="Authorization code from Google.")
    auth_finish.add_argument("--state", help="State value returned by auth-google.")
    auth_finish.add_argument(
        "--response-url",
        help="Full redirected localhost URL from the browser after Google approval.",
    )

    plan = sub.add_parser(
        "plan",
        help="Create or update a planned service record for later generation.",
    )
    plan.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    plan.add_argument(
        "--template-family",
        required=True,
        help="Template family slug, for example ordinary_after_pentecost.",
    )
    plan.add_argument(
        "--service-type-id",
        help="Override the default Planning Center service type ID.",
    )

    preview = sub.add_parser(
        "preview-service",
        help="Assemble booklet inputs for a date from the worksheet, ESV, and Planning Center.",
    )
    preview.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    preview.add_argument(
        "--template-family",
        required=True,
        help="Template family slug, for example ordinary_after_pentecost.",
    )
    preview.add_argument(
        "--service-type-id",
        help="Override the default Planning Center service type ID.",
    )
    preview.add_argument(
        "--skip-pco",
        action="store_true",
        help="Skip Planning Center lookup even if credentials are configured.",
    )
    preview.add_argument(
        "--skip-scripture",
        action="store_true",
        help="Skip ESV passage retrieval.",
    )

    analyze = sub.add_parser(
        "analyze-examples",
        help="Reverse-engineer a representative set of example liturgy docs into a markdown report.",
    )
    analyze.add_argument(
        "--output",
        type=lambda value: __import__('pathlib').Path(value),
        default=config_default_report_path(),
        help="Path for the generated markdown report.",
    )

    analyze_corpus = sub.add_parser(
        "analyze-corpus",
        help="Scan the broader Drive liturgy corpus and derive family rules.",
    )
    analyze_corpus.add_argument(
        "--output",
        type=lambda value: __import__('pathlib').Path(value),
        default=config_default_corpus_report_path(),
        help="Path for the generated markdown report.",
    )

    inspect_template = sub.add_parser(
        "inspect-template",
        help="Inspect the exact master Google Doc profile for a liturgy family.",
    )
    inspect_template.add_argument(
        "--family",
        required=True,
        help="Family slug such as ordinary_time, advent, lent, easter, palm_sunday.",
    )

    render_template = sub.add_parser(
        "render-template-profile",
        help="Render a markdown profile of the exact master Google Doc for a family.",
    )
    render_template.add_argument(
        "--family",
        required=True,
        help="Family slug such as ordinary_time, advent, lent, easter, palm_sunday.",
    )
    render_template.add_argument(
        "--output",
        type=lambda value: __import__('pathlib').Path(value),
        help="Optional output path for the rendered markdown profile.",
    )

    copy_template = sub.add_parser(
        "copy-template",
        help="Copy a Google Docs base template into the configured output folder.",
    )
    copy_template.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    copy_template.add_argument(
        "--template-family",
        required=True,
        help="Template family slug, for example ordinary_after_pentecost.",
    )
    copy_template.add_argument(
        "--doc-id",
        help="Override the configured source template doc ID.",
    )
    copy_template.add_argument(
        "--title",
        help="Override the destination Google Doc title.",
    )

    render_booklet = sub.add_parser(
        "render-booklet-plan",
        help="Build the exact paragraph replacement plan against a family master doc.",
    )
    render_booklet.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    render_booklet.add_argument(
        "--template-family",
        required=True,
        help="Template family slug, for example ordinary_time.",
    )
    render_booklet.add_argument(
        "--service-type-id",
        help="Override the default Planning Center service type ID.",
    )
    render_booklet.add_argument("--doc-id", help="Override the source doc used for plan building.")
    render_booklet.add_argument("--skip-pco", action="store_true", help="Skip Planning Center lookup.")
    render_booklet.add_argument("--skip-scripture", action="store_true", help="Skip ESV passage retrieval.")

    generate_booklet = sub.add_parser(
        "generate-booklet",
        help="Copy a family master doc and apply machine-managed booklet updates.",
    )
    generate_booklet.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    generate_booklet.add_argument(
        "--template-family",
        required=True,
        help="Template family slug, for example ordinary_time.",
    )
    generate_booklet.add_argument(
        "--service-type-id",
        help="Override the default Planning Center service type ID.",
    )
    generate_booklet.add_argument("--doc-id", help="Override the source template doc.")
    generate_booklet.add_argument("--title", help="Override the destination Google Doc title.")
    generate_booklet.add_argument("--skip-pco", action="store_true", help="Skip Planning Center lookup.")
    generate_booklet.add_argument("--skip-scripture", action="store_true", help="Skip ESV passage retrieval.")
    generate_booklet.add_argument(
        "--force-new",
        action="store_true",
        help="Create a second doc even if one is already recorded for that Sunday.",
    )
    generate_booklet.add_argument(
        "--dry-run",
        action="store_true",
        help="Assemble and render the mutation plan without copying or editing a Google Doc.",
    )
    generate_booklet.add_argument(
        "--attach-pdf-to-pco",
        action="store_true",
        help="Export the generated Google Doc as PDF and attach it to the matching Planning Center plan.",
    )

    update_booklet = sub.add_parser(
        "update-booklet",
        help="Update the existing generated booklet for a Sunday in place.",
    )
    update_booklet.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    update_booklet.add_argument(
        "--template-family",
        help="Optional template family override. Defaults to the stored family.",
    )
    update_booklet.add_argument(
        "--service-type-id",
        help="Override the default Planning Center service type ID.",
    )
    update_booklet.add_argument("--skip-pco", action="store_true", help="Skip Planning Center lookup.")
    update_booklet.add_argument("--skip-scripture", action="store_true", help="Skip ESV passage retrieval.")
    update_booklet.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the in-place update plan without mutating the Google Doc.",
    )
    update_booklet.add_argument(
        "--attach-pdf-to-pco",
        action="store_true",
        help="Export the updated Google Doc as PDF and attach it to the matching Planning Center plan.",
    )

    get_link = sub.add_parser(
        "get-booklet-link",
        help="Return the recorded Google Docs link for a generated Sunday booklet without editing it.",
    )
    get_link.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    get_link.add_argument(
        "--service-type-id",
        help="Override the default Planning Center service type ID.",
    )

    attach_pdf = sub.add_parser(
        "attach-booklet-pdf",
        help="Export an existing generated booklet as PDF and attach it to the matching Planning Center plan.",
    )
    attach_pdf.add_argument("--date", required=True, help="Service date in YYYY-MM-DD format.")
    attach_pdf.add_argument(
        "--service-type-id",
        help="Override the default Planning Center service type ID.",
    )
    attach_pdf.add_argument("--doc-id", help="Override the stored Google Doc ID.")
    attach_pdf.add_argument("--plan-id", help="Override the stored Planning Center plan ID.")
    attach_pdf.add_argument("--filename", help="Override the uploaded PDF filename.")

    return parser


def _default_title(template_family: str, service_date: str, observance: str | None = None) -> str:
    if observance:
        return observance
    prefix = {
        "ordinary_after_pentecost": "Ordinary Time",
        "ordinary_time": "Ordinary Time",
        "lent": "Lent",
        "advent": "Advent",
        "easter": "Easter",
    }.get(template_family, template_family.replace("_", " ").title())
    return f"{prefix} {service_date}"


def _default_source_doc_id(config, template_family: str) -> str:
    if template_family == "ordinary_after_pentecost":
        if not config.ordinary_template_doc_id:
            raise SystemExit("BOOKLET_ORDINARY_TEMPLATE_DOC_ID is not configured")
        return config.ordinary_template_doc_id
    return get_family_template(template_family).doc_id


def config_default_report_path():
    from pathlib import Path

    return Path("/home/ubuntu/pco-autoclaw/docs/booklet-example-analysis.md")


def config_default_corpus_report_path():
    from pathlib import Path

    return Path("/home/ubuntu/pco-autoclaw/docs/booklet-corpus-rules.md")


if __name__ == "__main__":
    raise SystemExit(main())
