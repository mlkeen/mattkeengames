# mattkeengames.com (Flask + Jinja)

A content-driven site for Matt Keen Games:
- Games library with rules + videos
- Kickstarter campaign blocks
- Simple blog/devlog

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Deploy on Railway

- Connect this repo to Railway
- Set the start command to: `gunicorn app:app`
- Add a custom domain: mattkeengames.com

## Add a new game

Create `content/games/<slug>.yml` and add an image under:
`static/images/games/<slug>/hero.jpg` (or update the path in YAML).
