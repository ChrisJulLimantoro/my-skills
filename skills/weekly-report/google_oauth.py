#!/usr/bin/env python3
"""Google OAuth helper for the /weekly-report skill.

Replaces the Google MCP servers with a normal Google OAuth 2.0 flow (the same
mechanism used by core/services/google_service.py in the weekly-report-generator
repo): one client-secret file, one token file, one combined-scope flow shared by
Calendar, Gmail, and Docs.

Subcommands (all emit JSON on stdout unless noted):
    auth                              Run/refresh OAuth; print "OK".
    calendar  --start ISO --end ISO  List calendar events in [start, end).
    forms     --after YYYY/MM/DD     List Google Forms receipt submissions.
    find-doc  --contains TERM [...]  Search Google Drive for Docs whose title
                                     contains every TERM (newest first).
    find-doc-email --after YYYY/MM/DD [--query Q]
                                     Fallback: search Gmail for weekly-report
                                     emails and extract Google Doc links/IDs.
    update-doc --id DOC_ID --file PATH
                                     Replace a Google Doc's body with file text.

Paths (override via env, else fall back to the repo defaults):
    GOOGLE_CLIENT_SECRET_FILE  OAuth client-secret JSON  (required for first auth)
    WEEKLY_REPORT_TOKEN_FILE   token cache (default: <skill>/google_token.json)

Times are returned as ISO-8601 with offsets; the skill renders them in WIB.
"""

import argparse
import base64
import json
import os
import re
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
# Repo defaults so the skill works out of the box on this machine. Override with env.
REPO_ROOT = "/home/julius/personal/gdp-labs-weekly-report-generator"
DEFAULT_CLIENT_SECRET = os.path.join(
    REPO_ROOT,
    "client_secret_802329956047-nvils0l6cmjbki4e3v9q4t8rc4h3h67q.apps.googleusercontent.com.json",
)
DEFAULT_TOKEN_FILE = os.path.join(SKILL_DIR, "google_token.json")

FORMS_RECEIPT_EMAIL = "forms-receipts-noreply@google.com"


def client_secret_file() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET_FILE", DEFAULT_CLIENT_SECRET)


def token_file() -> str:
    # Reuse the repo's existing token if present and no override was given.
    override = os.environ.get("WEEKLY_REPORT_TOKEN_FILE")
    if override:
        return override
    repo_token = os.path.join(REPO_ROOT, "tokens", "google_token.json")
    if os.path.exists(repo_token):
        return repo_token
    return DEFAULT_TOKEN_FILE


def get_credentials() -> Credentials:
    """Load, refresh, or interactively obtain OAuth credentials for all scopes."""
    path = token_file()
    creds = None
    if os.path.exists(path):
        try:
            # Load with the scopes actually granted in the token file (not the
            # required SCOPES) so we can detect when a new scope was added.
            granted = json.load(open(path)).get("scopes", [])
            if not set(SCOPES).issubset(set(granted)):
                creds = None  # missing a scope → force re-consent below
            else:
                creds = Credentials.from_authorized_user_file(path, SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        secret = client_secret_file()
        if not os.path.exists(secret):
            sys.exit(
                f"Client secret not found: {secret}\n"
                "Set GOOGLE_CLIENT_SECRET_FILE to your OAuth client JSON."
            )
        flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
        creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(creds.to_json())

    return creds


def service(api: str, version: str):
    return build(api, version, credentials=get_credentials())


def cmd_auth(_args) -> None:
    get_credentials()
    print("OK")


def cmd_calendar(args) -> None:
    svc = service("calendar", "v3")
    result = svc.events().list(
        calendarId="primary",
        timeMin=args.start,
        timeMax=args.end,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for ev in result.get("items", []):
        if ev.get("eventType") == "workingLocation":
            continue
        # acceptance filter: skip events the user explicitly declined
        declined = False
        for a in ev.get("attendees", []):
            if a.get("self") and a.get("responseStatus") == "declined":
                declined = True
        if declined:
            continue
        events.append({
            "summary": ev.get("summary", "(no title)"),
            "start": ev["start"].get("dateTime", ev["start"].get("date")),
            "end": ev["end"].get("dateTime", ev["end"].get("date")),
            "eventType": ev.get("eventType", "default"),
            "allDay": "date" in ev["start"],
        })
    json.dump(events, sys.stdout, indent=2)


def cmd_forms(args) -> None:
    svc = service("gmail", "v1")
    query = f"from:{FORMS_RECEIPT_EMAIL} after:{args.after}"
    listing = svc.users().messages().list(userId="me", q=query).execute()

    forms = []
    for m in listing.get("messages", []):
        msg = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        subject = headers.get("Subject", "")
        title = subject.replace("Response submitted:", "").strip()
        forms.append({"title": title, "date": headers.get("Date", "")})
    json.dump(forms, sys.stdout, indent=2)


def _extract_doc_links(text: str):
    ids = re.findall(r"/document/d/([a-zA-Z0-9-_]+)", text)
    return list(dict.fromkeys(ids))  # dedupe, keep order


def _message_text(payload) -> str:
    """Recursively pull decoded text from a Gmail message payload."""
    out = []
    data = payload.get("body", {}).get("data")
    if data:
        try:
            out.append(base64.urlsafe_b64decode(data).decode("utf-8", "replace"))
        except Exception:
            pass
    for part in payload.get("parts", []) or []:
        out.append(_message_text(part))
    return "\n".join(out)


def cmd_find_doc(args) -> None:
    """Search Google Drive for Docs whose title contains every --contains term."""
    svc = service("drive", "v3")
    clauses = ["mimeType='application/vnd.google-apps.document'", "trashed=false"]
    for term in args.contains:
        clauses.append("name contains '{}'".format(term.replace("'", "\\'")))
    query = " and ".join(clauses)

    result = svc.files().list(
        q=query,
        orderBy="modifiedTime desc",
        fields="files(id,name,modifiedTime)",
        pageSize=20,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    docs = []
    for f in result.get("files", []):
        docs.append({
            "id": f["id"],
            "name": f.get("name", ""),
            "modifiedTime": f.get("modifiedTime", ""),
            "link": f"https://docs.google.com/document/d/{f['id']}/edit",
        })
    json.dump(docs, sys.stdout, indent=2)


def cmd_find_doc_email(args) -> None:
    svc = service("gmail", "v1")
    query = f'{args.query} after:{args.after}'
    listing = svc.users().messages().list(userId="me", q=query).execute()

    hits = []
    for m in listing.get("messages", []):
        msg = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = _message_text(msg["payload"])
        doc_ids = _extract_doc_links(body)
        if doc_ids:
            hits.append({
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "doc_ids": doc_ids,
                "doc_links": [f"https://docs.google.com/document/d/{i}/edit" for i in doc_ids],
            })
    json.dump(hits, sys.stdout, indent=2)


def cmd_update_doc(args) -> None:
    with open(args.file, "r") as f:
        text_content = f.read()

    svc = service("docs", "v1")
    doc = svc.documents().get(documentId=args.id).execute()
    body_content = doc.get("body", {}).get("content", [])
    if body_content:
        end_index = body_content[-1].get("endIndex", 1)
        clear_end_index = max(1, end_index - 1)
    else:
        clear_end_index = 1

    requests = []
    if clear_end_index > 1:
        requests.append({
            "deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": clear_end_index}
            }
        })
    requests.append({
        "insertText": {"location": {"index": 1}, "text": text_content}
    })
    svc.documents().batchUpdate(documentId=args.id, body={"requests": requests}).execute()
    print(f"OK: updated document {args.id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth").set_defaults(func=cmd_auth)

    p_cal = sub.add_parser("calendar")
    p_cal.add_argument("--start", required=True, help="ISO-8601 timeMin")
    p_cal.add_argument("--end", required=True, help="ISO-8601 timeMax")
    p_cal.set_defaults(func=cmd_calendar)

    p_forms = sub.add_parser("forms")
    p_forms.add_argument("--after", required=True, help="YYYY/MM/DD")
    p_forms.set_defaults(func=cmd_forms)

    p_doc = sub.add_parser("find-doc")
    p_doc.add_argument(
        "--contains", action="append", required=True,
        help="Title substring that must appear (repeatable, all required)",
    )
    p_doc.set_defaults(func=cmd_find_doc)

    p_doc_email = sub.add_parser("find-doc-email")
    p_doc_email.add_argument("--after", required=True, help="YYYY/MM/DD")
    p_doc_email.add_argument("--query", default="weekly report", help="Gmail search terms")
    p_doc_email.set_defaults(func=cmd_find_doc_email)

    p_upd = sub.add_parser("update-doc")
    p_upd.add_argument("--id", required=True, help="Google Doc ID")
    p_upd.add_argument("--file", required=True, help="Path to markdown/text file")
    p_upd.set_defaults(func=cmd_update_doc)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
