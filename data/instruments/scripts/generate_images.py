"""Generate only the explicitly requested synthetic instrument illustrations."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".workshop" / "instrument-corpus" / "images"


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Image endpoint returned a redirect; stopped without forwarding authorization.")


def token():
    result = subprocess.run(
        ["az.cmd" if os.name == "nt" else "az", "account", "get-access-token",
         "--resource", "https://cognitiveservices.azure.com",
         "--query", "accessToken", "--output", "tsv"],
        capture_output=True, text=True, timeout=90, check=False,
    )
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("Entra token acquisition failed. Run az login for the approved account.")
    return result.stdout.strip()


def prompt_for(item, view):
    composition = (
        "High-end studio product photograph, three-quarter view, physically credible materials, "
        "restrained neutral background, soft shadows, the whole instrument visible with generous margins."
        if view == "hero" else
        "Technical product photograph, straight frontal view or true side view for a horizontal instrument. "
        "Place the complete instrument centrally on a plain white background, with its major parts clearly visible. "
        "Keep the entire instrument inside the central 70 percent of the frame, no perspective distortion."
    )
    return (
        f"{composition} Subject: {item['image']}. "
        f"Illustrative fictional {item['flagship']} by Aster Vale Instruments. "
        "Exactly one instrument. No people, no branding, no letters, no text, no labels, no arrows, "
        "no measurements, no decorative objects. Anatomically credible construction. "
        "Landscape composition for horizontal instruments; portrait composition otherwise."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--slug")
    parser.add_argument("--view", choices=["hero", "anatomy"])
    parser.add_argument("--retries", type=int, default=0,
                        help="Approved retries per image; network retries may incur additional charges.")
    args = parser.parse_args()
    parsed = urlparse(args.endpoint)
    if (parsed.scheme != "https" or not parsed.hostname
            or not parsed.hostname.endswith(".services.ai.azure.com")
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.port not in (None, 443)):
        parser.error("Use an HTTPS Foundry resource endpoint without credentials or query parameters.")
    if not 1 <= args.limit <= 40:
        parser.error("--limit must be between 1 and 40; no implicit paid retries are performed.")
    if not 0 <= args.retries <= 5:
        parser.error("--retries must be between 0 and 5; unattended execution is bounded.")
    instruments = json.loads((CORPUS / "catalog.json").read_text(encoding="utf-8"))["instruments"]
    if args.slug:
        instruments = [item for item in instruments if item["slug"] == args.slug]
        if not instruments:
            parser.error("Unknown instrument slug.")
    CACHE.mkdir(parents=True, exist_ok=True)
    generated = 0
    for item in instruments:
        for view in ([args.view] if args.view else ["hero", "anatomy"]):
            path = CACHE / f"{item['slug']}-{view}.png"
            receipt = path.with_suffix(".json")
            prompt = prompt_for(item, view)
            digest = hashlib.sha256(prompt.encode()).hexdigest()
            if path.exists() and receipt.exists():
                saved = json.loads(receipt.read_text(encoding="utf-8"))
                if (saved["prompt_sha256"] != digest or saved["deployment"] != args.deployment
                        or saved["image_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()):
                    raise RuntimeError(f"Cache mismatch for {path.name}; preserve it and select a deliberate regeneration.")
                print(f"Cached: {path.name}", flush=True)
                continue
            if path.exists() or receipt.exists():
                raise RuntimeError(f"Incomplete cache pair for {path.name}; inspect it before another paid request.")
            if generated >= args.limit:
                raise RuntimeError(f"Request limit reached; {generated} images generated this invocation.")
            payload = {"model": args.deployment, "prompt": prompt, "width": 1024, "height": 1024,
                       "web_grounding": False, "auto_aspect_ratio": False}
            print(f"Generating {path.name} (request {generated + 1}/{args.limit})", flush=True)
            for attempt in range(args.retries + 1):
                request = Request(
                    f"https://{parsed.hostname}/mai/v1/images/generations",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token()}"},
                    method="POST",
                )
                try:
                    with build_opener(NoRedirects()).open(request, timeout=240) as response:
                        result = json.load(response)
                        request_id = response.headers.get("apim-request-id") or response.headers.get("x-request-id")
                    break
                except HTTPError as error:
                    correlation = error.headers.get("apim-request-id") or error.headers.get("x-request-id")
                    retryable = error.code in (408, 429, 500, 502, 503, 504)
                    diagnostic = f"HTTP {error.code}; correlation={correlation}"
                except (URLError, TimeoutError, ConnectionError) as error:
                    retryable = True
                    reason = getattr(error, "reason", error)
                    diagnostic = f"Transport failure ({type(reason).__name__}); billing outcome uncertain"
                if not retryable or attempt == args.retries:
                    raise RuntimeError(
                        f"{path.name}: {diagnostic}; stopped after {attempt + 1} attempts. "
                        "Existing images retained; no cloud resources modified."
                    ) from None
                delay = min(60, 10 * 2 ** attempt)
                print(f"{diagnostic}; approved retry {attempt + 1}/{args.retries} after {delay}s",
                      flush=True)
                time.sleep(delay)
            data = result.get("data", [])
            if len(data) != 1 or not isinstance(data[0].get("b64_json"), str):
                raise RuntimeError("Unexpected image response shape; no image saved and no retry performed.")
            binary = base64.b64decode(data[0]["b64_json"], validate=True)
            if not binary.startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError("Image response is not a PNG; no image saved.")
            temporary = path.with_suffix(".png.partial")
            temporary.write_bytes(binary)
            temporary.replace(path)
            receipt.write_text(json.dumps({
                "deployment": args.deployment, "prompt_sha256": digest,
                "image_sha256": hashlib.sha256(binary).hexdigest(),
                "request_id": request_id, "synthetic": True,
            }, indent=2) + "\n", encoding="utf-8")
            generated += 1
            print(f"Saved {path.name}: {len(binary)} bytes", flush=True)
    print(f"Completed: {generated} new images; no Azure resources created, modified or deleted.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
