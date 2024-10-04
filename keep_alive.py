from flask import Flask, render_template_string
from threading import Thread
import os

app = Flask(__name__)


@app.route(
    "/",
    methods=[
        "GET",
        "POST",
        "CONNECT",
        "PUT",
        "DELETE",
        "PATCH",
        "OPTIONS",
        "TRACE",
        "HEAD",
    ],
)
def main():
    return "I'm alive!"


def run():
    port = int(os.getenv('PORT', 3000))  # Ensure you're using Render's dynamically assigned port
    print(f"Starting Flask on port {port}")  # Log the port number

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def keep_alive():
    server = Thread(target=run)
    server.start()
