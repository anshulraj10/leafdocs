import argparse
import os

from leafdocs import LeafDocs

DEFAULT_DOCS_DIR = "./docs"
DEFAULT_PORT = 5000

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a local leafdocs dev server.")
    parser.add_argument("--docs-dir", default=DEFAULT_DOCS_DIR,
                        help=f"Markdown directory (default: {DEFAULT_DOCS_DIR})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    # Plain-http local run: Secure cookies would cause a login loop.
    # setdefault keeps any value you set in .env or the shell.
    os.environ.setdefault("LEAFDOCS_COOKIE_SECURE", "false")
    ld = LeafDocs(docs_dir=args.docs_dir)
    app = ld.flask_app
    ld.run(port=args.port, debug=True)
else:
    ld = LeafDocs(docs_dir=DEFAULT_DOCS_DIR)
    app = ld.flask_app
