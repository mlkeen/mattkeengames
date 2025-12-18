import os
import pathlib
import datetime as dt
from flask import Flask, render_template, abort, url_for
import yaml
import markdown as md

BASE_DIR = pathlib.Path(__file__).resolve().parent
CONTENT_DIR = BASE_DIR / "content"
GAMES_DIR = CONTENT_DIR / "games"
BLOG_DIR = CONTENT_DIR / "blog"
PAGES_DIR = CONTENT_DIR / "pages"

def load_yaml(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_markdown(path: pathlib.Path) -> dict:
    """
    Returns dict with: title (optional), date (optional), html, raw
    Supports simple frontmatter:
    ---
    title: Something
    date: 2025-01-01
    ---
    Markdown content...
    """
    raw = path.read_text(encoding="utf-8")
    title = None
    date = None
    body = raw

    if raw.lstrip().startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            body = parts[2]
            meta = yaml.safe_load(fm) or {}
            title = meta.get("title")
            date = meta.get("date")

    html = md.markdown(body, extensions=["extra", "tables", "toc"])
    return {"title": title, "date": date, "html": html, "raw": raw}

def load_all_games() -> list[dict]:
    games = []
    if not GAMES_DIR.exists():
        return games
    for p in sorted(GAMES_DIR.glob("*.yml")):
        g = load_yaml(p)
        if not g:
            continue
        g.setdefault("slug", p.stem)
        games.append(g)
    # sort: featured first, then title
    games.sort(key=lambda x: (not bool(x.get("featured", False)), x.get("title","").lower()))
    return games

def get_game(slug: str) -> dict | None:
    path = GAMES_DIR / f"{slug}.yml"
    if not path.exists():
        return None
    g = load_yaml(path)
    g.setdefault("slug", slug)
    return g

def get_blog_posts() -> list[dict]:
    posts = []
    if not BLOG_DIR.exists():
        return posts
    for p in sorted(BLOG_DIR.glob("*.md")):
        data = load_markdown(p)
        slug = p.stem
        title = data["title"] or slug.replace("-", " ").title()
        date = data["date"]
        # parse date if present
        parsed = None
        if date:
            try:
                parsed = dt.date.fromisoformat(str(date))
            except Exception:
                parsed = None
        posts.append({
            "slug": slug,
            "title": title,
            "date": parsed,
            "html": data["html"],
        })
    # newest first (None dates last)
    posts.sort(key=lambda x: (x["date"] is None, dt.date.min if x["date"] is None else -x["date"].toordinal()))
    return posts

def get_page(slug: str) -> dict | None:
    path = PAGES_DIR / f"{slug}.md"
    if not path.exists():
        return None
    data = load_markdown(path)
    title = data["title"] or slug.replace("-", " ").title()
    return {"slug": slug, "title": title, "html": data["html"]}

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.context_processor
    def inject_globals():
        return {
            "site_name": "Matt Keen Games",
            "now_year": dt.datetime.now().year
        }

    @app.route("/")
    def home():
        games = load_all_games()
        featured = next((g for g in games if g.get("featured")), None) or (games[0] if games else None)
        posts = get_blog_posts()[:3]
        return render_template("home.html", featured=featured, games=games[:6], posts=posts)

    @app.route("/games")
    def games_index():
        games = load_all_games()
        return render_template("games/index.html", games=games)

    @app.route("/games/<slug>")
    def game_detail(slug):
        game = get_game(slug)
        if not game:
            abort(404)
        return render_template("games/detail.html", game=game)

    @app.route("/blog")
    def blog_index():
        posts = get_blog_posts()
        return render_template("blog/index.html", posts=posts)

    @app.route("/blog/<slug>")
    def blog_post(slug):
        path = BLOG_DIR / f"{slug}.md"
        if not path.exists():
            abort(404)
        data = load_markdown(path)
        title = data["title"] or slug.replace("-", " ").title()
        date = data["date"]
        return render_template("blog/post.html", title=title, date=date, html=data["html"], slug=slug)

    @app.route("/pages/<slug>")
    def page(slug):
        pg = get_page(slug)
        if not pg:
            abort(404)
        return render_template("page.html", page=pg)

    @app.route("/about")
    def about():
        pg = get_page("about")
        if not pg:
            abort(404)
        return render_template("page.html", page=pg)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
