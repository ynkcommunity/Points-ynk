from flask import Flask

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

# This line is only for local testing; it should not be in production.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10101, debug=False)
