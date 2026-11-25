#!/usr/bin/env python3
"""Inspect one local HTML export. Standard library only; never makes requests."""

from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

VERSION = "1.0.0"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NON_CONTENT = {"head", "script", "style", "nav", "footer", "aside", "form", "template", "noscript"}


class ExportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.title = []
        self.headings = []
        self.text = []
        self.article_text = []
        self.links = []
        self.images = []
        self.canonicals = []
        self.schema = []
        self.schema_buffer = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        style = re.sub(r"\s+", "", attrs.get("style", "")).lower()
        hidden = "hidden" in attrs or attrs.get("aria-hidden", "").lower() == "true"
        hidden = hidden or "display:none" in style or "visibility:hidden" in style
        suppressed = hidden or any(item[1] for item in self.stack)
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        if tag == "script" and attrs.get("type", "").lower().split(";", 1)[0].strip() == "application/ld+json":
            self.schema_buffer = []
        if not suppressed and not any(item[0] in NON_CONTENT for item in self.stack):
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                self.headings.append({"level": int(tag[1]), "text": ""})
            if tag == "a" and "href" in attrs:
                self.links.append(attrs["href"])
            if tag == "img":
                self.images.append({"src": attrs.get("src", ""), "alt_present": "alt" in attrs})
        if tag not in VOID:
            self.stack.append((tag, suppressed))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "script" and self.schema_buffer is not None:
            self.schema.append("".join(self.schema_buffer))
            self.schema_buffer = None
        # Recover from mismatched closing tags; this is not an HTML validator.
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        tags = [item[0] for item in self.stack]
        if self.schema_buffer is not None and "script" in tags:
            self.schema_buffer.append(data)
        if "title" in tags:
            self.title.append(data)
        if any(item[1] for item in self.stack) or any(tag in NON_CONTENT for tag in tags):
            return
        self.text.append(data)
        if "article" in tags:
            self.article_text.append(data)
        if self.headings and any(tag in {"h1", "h2", "h3", "h4", "h5", "h6"} for tag in tags):
            self.headings[-1]["text"] += data


def schema_types(value):
    result = set()
    if isinstance(value, list):
        for item in value:
            result.update(schema_types(item))
    elif isinstance(value, dict):
        kind = value.get("@type", [])
        if isinstance(kind, str):
            result.add(kind)
        elif isinstance(kind, list):
            result.update(item for item in kind if isinstance(item, str))
        if "@graph" in value:
            result.update(schema_types(value["@graph"]))
    return result


def inspect_html(html: str) -> dict:
    parser = ExportParser()
    parser.feed(html)
    parser.close()
    findings = []

    def add(severity, code, message):
        findings.append({"severity": severity, "code": code, "message": message})

    title = " ".join("".join(parser.title).split())
    if not title:
        add("warning", "missing_title", "No document title in this export. Check the final CMS page.")
    h1_count = sum(h["level"] == 1 for h in parser.headings)
    if h1_count != 1:
        add("warning", "h1_count", f"Found {h1_count} visible H1 elements. Review the page heading.")
    if len(parser.canonicals) != 1:
        add("warning", "canonical_count", f"Found {len(parser.canonicals)} canonical elements. Verify the final page URL.")
    elif urlsplit(parser.canonicals[0]).scheme not in {"https", "http"}:
        add("warning", "relative_canonical", "Canonical is not an absolute HTTP(S) URL.")
    invalid = []
    types = set()
    for number, block in enumerate(parser.schema, 1):
        try:
            value = json.loads(block, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            if not isinstance(value, (dict, list)):
                raise ValueError("Expected an object or array")
            types.update(schema_types(value))
        except (ValueError, RecursionError) as error:
            invalid.append({"block": number, "error": str(error)[:180]})
            add("error", "invalid_json_ld", f"JSON-LD block {number} is not valid JSON or is not an object/array.")
    if not parser.schema:
        add("info", "no_json_ld", "No JSON-LD in the export. CMS plugins may add it to the final page; it is not a citation requirement.")
    if any(urlsplit(href.strip()).scheme.lower() in {"javascript", "data", "vbscript"} for href in parser.links):
        add("warning", "active_link", "A link uses a script or data URL. Review before publishing.")
    missing_alt = sum(not image["alt_present"] for image in parser.images)
    if missing_alt:
        add("warning", "missing_alt", f"{missing_alt} images have no alt attribute. Empty alt is allowed for decorative images.")
    text = " ".join(" ".join(parser.article_text or parser.text).split())
    if not text:
        add("warning", "no_text", "No static article text was found. The tool does not render JavaScript.")
    return {
        "version": VERSION,
        "title": title,
        "h1_count": h1_count,
        "headings": parser.headings,
        "words": len(re.findall(r"\b\w+(?:[-']\w+)*\b", text)),
        "text_scope": "article" if parser.article_text else "document",
        "canonicals": parser.canonicals,
        "links_found": len(parser.links),
        "images_found": len(parser.images),
        "json_ld": {"blocks": len(parser.schema), "types": sorted(types), "invalid": invalid},
        "counts": dict(Counter(f["severity"] for f in findings)),
        "findings": findings,
        "limits": "Local HTML heuristic only. No requests, rendering, index checks, full Schema.org validation, content-quality rating or prediction of AI citations.",
    }


def main(argv=None):
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("file", type=Path, help="Local UTF-8 HTML file (maximum 5 MiB)")
    argument_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    argument_parser.add_argument("--fail-on", choices=["error", "warning", "never"], default="error")
    args = argument_parser.parse_args(argv)
    try:
        if args.file.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("Input is larger than 5 MiB")
        result = inspect_html(args.file.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, RecursionError) as error:
        argument_parser.error(str(error))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Article Check {VERSION}: {result['title'] or '(no title)'}")
        print(f"Words: {result['words']}; H1: {result['h1_count']}; JSON-LD blocks: {result['json_ld']['blocks']}")
        for finding in result["findings"]:
            print(f"{finding['severity'].upper()} {finding['code']}: {finding['message']}")
        print(result["limits"])
    fail = result["counts"].get("error", 0) > 0
    if args.fail_on == "warning":
        fail = fail or result["counts"].get("warning", 0) > 0
    return int(fail and args.fail_on != "never")


if __name__ == "__main__":
    sys.exit(main())
