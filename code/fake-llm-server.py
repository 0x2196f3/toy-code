import json
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


HOST = "0.0.0.0"
PORT = 8000

rng = random.SystemRandom()


WORDS = [
    "amber",
    "ancient",
    " autumn",
    "blue",
    "bright",
    "calm",
    "celestial",
    "crystal",
    "digital",
    "distant",
    "electric",
    "emerald",
    "fading",
    "floating",
    "golden",
    "hidden",
    "lunar",
    "midnight",
    "misty",
    "northern",
    "quiet",
    "rapid",
    "red",
    "remote",
    "silver",
    "silent",
    "soft",
    "solar",
    "stellar",
    "violet",
    "wandering",
    "warm",
    "whispering",
    "wild",
]

SENTENCE_TEMPLATES = [
    "The {word1} signal crosses the {word2} horizon.",
    "A {word1} pattern emerges from the {word2} noise.",
    "The {word1} system observes a {word2} sequence.",
    "Several {word1} fragments form a {word2} response.",
    "The {word1} process continues through the {word2} channel.",
    "A {word1} message is assembled from {word2} components.",
    "The {word1} result changes according to the {word2} state.",
    "A {word1} value appears beside a {word2} marker.",
]


def choose_word():
    return rng.choice(WORDS).strip()


def random_sentence():
    template = rng.choice(SENTENCE_TEMPLATES)

    return template.format(
        word1=choose_word(),
        word2=choose_word(),
    )


def random_text(sentence_count=None):
    if sentence_count is None:
        sentence_count = rng.randint(1, 3)

    return " ".join(random_sentence() for _ in range(sentence_count))


def random_model_name():
    first = choose_word()
    second = choose_word()

    while second == first:
        second = choose_word()

    return f"{first}-{second}"


def create_models(count=8):
    models = []
    used_names = set()

    while len(models) < count:
        name = random_model_name()

        if name in used_names:
            continue

        used_names.add(name)
        models.append(
            {
                "id": name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "random-api",
            }
        )

    return models


MODELS = create_models()


def get_random_response_content():
    actual_output = random_text()

    if rng.random() < 0.5:
        thought_process = random_text(sentence_count=rng.randint(1, 2))

        return (
            f"<think>\n"
            f"{thought_process}\n"
            f"</think>\n"
            f"{actual_output}"
        )

    return actual_output


def read_request_body(handler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length)

    if not raw_body:
        return {}

    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw_body.decode("utf-8", errors="replace")


def print_request(handler, body):
    parsed_url = urlparse(handler.path)

    request_info = {
        "method": handler.command,
        "path": parsed_url.path,
        "query": parsed_url.query,
        "headers": dict(handler.headers),
        "body": body,
    }

    print(
        json.dumps(
            request_info,
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )


class OpenAICompatibleHandler(BaseHTTPRequestHandler):
    server_version = "RandomOpenAIAPI/1.0"

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PUT(self):
        self.handle_request()

    def do_PATCH(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def handle_request(self):
        body = read_request_body(self)

        print_request(self, body)

        path = urlparse(self.path).path

        if path == "/v1/models":
            response = self.models_list()

        elif path.startswith("/v1/models/"):
            model_id = path.removeprefix("/v1/models/")
            response = self.single_model(model_id)

        elif path == "/v1/chat/completions":
            response = self.chat_completion(body)

        elif path == "/v1/responses":
            response = self.responses_api(body)

        elif path == "/health":
            response = {"status": "ok"}

        else:
            response = {
                "ok": True,
                "result": get_random_response_content(),
            }

        self.send_json(response)

    def models_list(self):
        return {
            "object": "list",
            "data": MODELS,
        }

    def single_model(self, model_id):
        for model in MODELS:
            if model["id"] == model_id:
                return model

        return {
            "id": model_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "random-api",
        }

    def chat_completion(self, body):
        if not isinstance(body, dict):
            body = {}

        content = get_random_response_content()

        return {
            "id": f"chatcmpl-{random_model_name()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", MODELS[0]["id"]),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": len(content.split()),
                "total_tokens": len(content.split()),
            },
        }

    def responses_api(self, body):
        if not isinstance(body, dict):
            body = {}

        content = get_random_response_content()

        return {
            "id": f"resp-{random_model_name()}",
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "model": body.get("model", MODELS[0]["id"]),
            "output": [
                {
                    "type": "message",
                    "id": f"msg-{random_model_name()}",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": content,
                        }
                    ],
                }
            ],
        }

    def send_json(self, data, status=200):
        response_body = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        )

    def log_message(self, format_string, *args):
        sys.stderr.write(
            "%s - - [%s] %s\n"
            % (
                self.address_string(),
                self.log_date_time_string(),
                format_string % args,
            )
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        (HOST, PORT),
        OpenAICompatibleHandler,
    )

    print(f"Listening on http://{HOST}:{PORT}", flush=True)
    print("Available models:", flush=True)

    for model in MODELS:
        print(f"  - {model['id']}", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...", flush=True)
        server.shutdown()
        server.server_close()
