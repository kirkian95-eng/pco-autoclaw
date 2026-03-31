---
name: sunday-booklet
description: Preview and generate Sunday morning liturgy booklet inputs
user-invocable: true
---

# Sunday Booklet

Builds the weekly Sunday liturgy booklet by combining ACNA lectionary data, ESV scripture text, Planning Center assignments, and a Google Docs template.

## Commands

All commands go through:

```bash
booklet.sh <command> [args]
```

### Preview a Sunday

```bash
booklet.sh preview 2026-06-07
booklet.sh preview-no-pco 2026-06-07    # without Planning Center data
```

### Generate / Update / Link

```bash
booklet.sh make-reply 2026-06-07 ordinary_time     # create if missing + attach PDF to PCO
booklet.sh update-reply 2026-06-07 ordinary_time   # update existing doc + refresh PDF
booklet.sh link-reply 2026-06-07                    # return existing doc URL only
```

### Natural Language

```bash
booklet.sh route-reply "make a booklet for Trinity Sunday"
booklet.sh route-reply "what songs are we singing next week?"
```

### PDF Attachment

```bash
booklet.sh attach-booklet-pdf-reply 2026-06-07     # export PDF + attach to PCO plan
```

## Configuration

Set in `config.env`:
- `BOOKLET_SERVICE_TYPE_ID` — PCO service type for weekly worship
- `BOOKLET_ORDINARY_TEMPLATE_DOC_ID` — Google Docs template ID
- `BOOKLET_GOOGLE_TEMPLATE_ROOT_ID` — Drive folder with templates
- `BOOKLET_GOOGLE_OUTPUT_ROOT_ID` — Drive folder for generated docs
- `ESV_API_TOKEN` — Crossway ESV API key
- `NAME_ALIASES` — initials-to-name map (e.g. `JAM:James,KT:Kim`)

## Rules

1. Human edits in Google Docs are authoritative — never overwrite them.
2. `make` = create-if-missing only. `update` = mutate existing. `link` = return URL only.
3. Making/updating a booklet does not notify anyone and does not require approval.
