import os

from leafdocs import LeafDocs

if __name__ == "__main__":
    # Plain-http local run: Secure cookies would cause a login loop.
    # setdefault keeps any value you set in .env or the shell.
    os.environ.setdefault("LEAFDOCS_COOKIE_SECURE", "false")

ld = LeafDocs(docs_dir="./docs")
app = ld.flask_app

if __name__ == "__main__":
    ld.run(debug=True)
