---
name: Doc2X-convert
description: "Use when the user asks to parse, convert, or recognize a PDF or image - e.g. PDF to Markdown/LaTeX/Word, extracting formulas or tables, OCR of document screenshots. PDF conversion is the default entry; image conversion (jpg/png) only when the user explicitly asks for image conversion."
---

# Doc2X-convert: PDF / image parsing via Doc2X API

Convert documents to editable formats with the Doc2X API (formulas, tables,
and layout preserved). Full API docs: https://doc2x.noedgeai.com/help/zh-cn/

## When to use

- **PDF (default)**: user asks to parse / convert / recognize a PDF. Output:
  `md`, `tex`, or `docx`.
- **Image**: only when the user explicitly asks to convert an image
  (jpg/png, <= 7M). Output is Markdown.

## Prerequisites

The API key is read from the `DOC2X_API_KEY` environment variable. If it is
missing, tell the user how to set it up (do not ask them to paste the key
into the conversation if avoidable):

1. Get a key at https://open.noedgeai.com (format `sk-xxx`)
2. `setx DOC2X_API_KEY "sk-xxx"` and restart the terminal

## Usage

```bash
python "<skill-dir>/scripts/doc2x_convert.py" <file> [--to md|tex|docx] [--out DIR] [--model v2|v3-2026]
```

- `--to` defaults to `md` (formulas exported as `$...$`). Use `docx` when the
  user wants a Word file, `tex` for LaTeX.
- Default output directory: `<file>_doc2x/` next to the input file.
- The script picks the flow automatically: `.pdf` -> PDF pipeline,
  `.jpg/.jpeg/.png` -> image pipeline (always Markdown output).

## Workflow

1. Confirm the target format from the user's request (default: markdown).
2. Run the script with the file path. Progress goes to stderr.
3. Check the output directory exists and list its contents.
4. Report the output path to the user and briefly summarize the extracted
   content (open the markdown to verify formulas/tables converted cleanly).

## Limits

- Cloud results are kept only 24h, but the script downloads immediately, so
  this is transparent.
- PDF: <= 300M, <= 2000 pages, parse timeout 15 min. Image: <= 7M, jpg/png.
- Rate limit: HTTP 429 means back off and retry later.
- Errors are printed in Chinese with a hint; relay them to the user as-is.
