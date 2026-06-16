"""
sync.py — Lee Google Drive recursivamente y genera un sitio estático en /dist
"""

import os
import io
import json
import shutil
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── Config ──────────────────────────────────────────────────────────────────
ROOT_FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]
SITE_TITLE     = os.environ.get("SITE_TITLE", "Cursos")
SA_JSON        = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
DIST_DIR       = Path("dist")
TEMPLATE_DIR   = Path("site-template")
SCOPES         = ["https://www.googleapis.com/auth/drive.readonly"]

# ── Auth ─────────────────────────────────────────────────────────────────────
creds   = service_account.Credentials.from_service_account_info(
              json.loads(SA_JSON), scopes=SCOPES)
service = build("drive", "v3", credentials=creds)


# ── Drive helpers ─────────────────────────────────────────────────────────────
def list_children(folder_id: str) -> list[dict]:
    """Returns all files and folders inside a Drive folder (non-recursive)."""
    results, page_token = [], None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            orderBy="name",
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def download_file(file_id: str, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


# ── Tree builder ──────────────────────────────────────────────────────────────
FOLDER_MIME = "application/vnd.google-apps.folder"

def build_tree(folder_id: str, rel_path: Path, depth: int = 0) -> list[dict]:
    """
    Recursively walks Drive. Returns a list of node dicts:
      { type: "folder"|"file", name, rel_path, children?, file_id? }
    Also downloads HTML files into dist/.
    """
    nodes = []
    for item in list_children(folder_id):
        name      = item["name"]
        mime      = item["mimeType"]
        node_path = rel_path / slugify(name)

        if mime == FOLDER_MIME:
            children = build_tree(item["id"], node_path, depth + 1)
            nodes.append({
                "type":     "folder",
                "name":     name,
                "rel_path": node_path,
                "children": children,
            })
        elif name.endswith(".html"):
            dest = DIST_DIR / rel_path / name
            print(f"  Downloading: {dest}")
            download_file(item["id"], dest)
            nodes.append({
                "type":     "file",
                "name":     name,
                "rel_path": rel_path / name,
                "file_id":  item["id"],
            })
        else:
            # Download other assets (CSS, JS, images) as-is
            dest = DIST_DIR / node_path / name
            print(f"  Asset: {dest}")
            download_file(item["id"], dest)

    return nodes


def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^\w\-\.]", "", text)  # ← agrega \. para preservar puntos
    return text


# ── Index generators ──────────────────────────────────────────────────────────
def css_link() -> str:
    return '<link rel="stylesheet" href="/cursos/assets/style.css">'


def card_grid(items: list[dict], current_depth_path: Path) -> str:
    cards = []
    for node in items:
        if node["type"] == "folder":
            href  = f"/cursos/{node['rel_path']}/"
            label = node["name"]
            icon  = "📁"
            meta  = f'{len(node["children"])} elemento(s)'
        else:
            href  = f"/cursos/{node['rel_path']}"
            label = node["name"].removesuffix(".html")
            icon  = "📄"
            meta  = "Página HTML"

        cards.append(f"""
        <a class="card" href="{href}">
          <span class="card-icon">{icon}</span>
          <span class="card-title">{label}</span>
          <span class="card-meta">{meta}</span>
        </a>""")

    return "\n".join(cards)


def render_index(title: str, breadcrumb: str, items: list[dict],
                 dest: Path, depth_path: Path):
    dest.mkdir(parents=True, exist_ok=True)
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — {SITE_TITLE}</title>
  {css_link()}
</head>
<body>
  <header>
    <a class="site-name" href="/cursos/">{SITE_TITLE}</a>
    <nav class="breadcrumb">{breadcrumb}</nav>
  </header>
  <main>
    <h1>{title}</h1>
    <div class="grid">
      {card_grid(items, depth_path)}
    </div>
  </main>
</body>
</html>"""
    (dest / "index.html").write_text(html, encoding="utf-8")


def generate_indexes(nodes: list[dict], parent_path: Path,
                     breadcrumb_html: str, title: str):
    render_index(title, breadcrumb_html, nodes, DIST_DIR / parent_path, parent_path)

    for node in nodes:
        if node["type"] == "folder":
            crumb = (breadcrumb_html +
                     f' / <a href="/cursos/{node["rel_path"]}/">{node["name"]}</a>')
            generate_indexes(
                node["children"],
                node["rel_path"],
                crumb,
                node["name"],
            )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Clean dist
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()

    # Copy static assets from template
    assets_src = TEMPLATE_DIR / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, DIST_DIR / "assets")

    print("Walking Drive…")
    tree = build_tree(ROOT_FOLDER_ID, Path(""), depth=0)

    print("Generating index files…")
    root_crumb = f'<a href="/cursos/">{SITE_TITLE}</a>'
    generate_indexes(tree, Path(""), root_crumb, SITE_TITLE)

    print(f"Done. Files in {DIST_DIR}:")
    for p in sorted(DIST_DIR.rglob("*")):
        print(" ", p)


if __name__ == "__main__":
    main()
