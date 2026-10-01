"""One Responses turn per command; approval is explicit and never automatic."""
import argparse
import json
import secrets
import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError
from azure.identity import AzureCliCredential
from openai import APIConnectionError, APIStatusError, APITimeoutError

from lab07 import checked_version, fingerprint, private_path, read_config, save

PROMPT = (
    "Read complaint-003. Summarize its instrument, issue and status. Find an active partner "
    "in the customer's country supporting its instrument family and required service. "
    "Show both IDs and eligibility facts. Do not change anything."
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["start", "approve", "reject"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True, help="Deployment receipt")
    parser.add_argument("--conversation", type=Path, required=True, help="Separate private Responses receipt")
    parser.add_argument("--approval-id")
    parser.add_argument("--prompt", default=PROMPT)
    return parser.parse_args()


def run(args):
    config = read_config(args.config)
    conversation_path = private_path(args.conversation)
    if conversation_path in (args.config.resolve(), args.state.resolve()):
        raise ValueError("Use separate configuration, deployment and conversation files")
    receipt = json.loads(private_path(args.state).read_text(encoding="utf-8"))
    if receipt.get("config") != fingerprint(config) or "version" not in receipt or receipt.get("status") != "active":
        raise RuntimeError("A matching active deployment receipt is required")
    if args.operation == "start":
        if conversation_path.exists():
            raise RuntimeError("Use a new conversation filename to reset; do not overwrite an existing chain")
        if args.approval_id:
            raise ValueError("An approval ID is valid only for approve/reject")
        request = {"input": args.prompt}
    else:
        conversation = json.loads(conversation_path.read_text(encoding="utf-8"))
        if conversation.get("config") != fingerprint(config):
            raise RuntimeError("Conversation belongs to another deployment")
        pending = [item for item in conversation["response"]["output"] if item["type"] == "mcp_approval_request"]
        if not args.approval_id or args.approval_id not in {item["id"] for item in pending}:
            raise ValueError("Specify an approval ID from this conversation's last response")
        request = {
            "previous_response_id": conversation["response"]["id"],
            "input": [{"type": "mcp_approval_response", "approval_request_id": args.approval_id,
                       "approve": args.operation == "approve"}],
        }
    trace_id = secrets.token_hex(16)
    traceparent = f"00-{trace_id}-{secrets.token_hex(8)}-01"
    # Persist intent before sending; an uncertain result is not safe to replay.
    intent = conversation_path.with_suffix(".pending.json")
    if intent.exists():
        raise RuntimeError("Previous turn outcome is uncertain; inspect its pending receipt instead of replaying")
    with intent.open("x", encoding="utf-8") as stream:
        json.dump({"operation": args.operation, "trace_id": trace_id, "config": fingerprint(config)}, stream)
    with AIProjectClient(endpoint=config["project_endpoint"], credential=AzureCliCredential(),
                         allow_preview=True, retry_total=0) as project:
        version = checked_version(project, config, receipt)
        if str(version.status) != "active":
            raise RuntimeError("Recorded version is not active")
        versions = list(project.agents.list_versions(config["agent_name"]))
        if len(versions) != 1 or str(versions[0].version) != receipt["version"]:
            raise RuntimeError("Named endpoint may route another version; do not invoke an unqualified version")
        with project.get_openai_client(agent_name=config["agent_name"], max_retries=0, timeout=180) as client:
            raw = client.responses.with_raw_response.create(
                **request, stream=False, extra_headers={"traceparent": traceparent},
            )
            response = raw.parse().model_dump(mode="json", exclude_none=True)
            save(conversation_path, {"config": fingerprint(config), "trace_id": trace_id,
                                     "request_id": raw.headers.get("x-ms-request-id"),
                                     "response": response})
            intent.unlink()
    print("Trace ID:", trace_id)
    print("Response ID:", response["id"])
    print("Status:", response["status"])
    for item in response.get("output", []):
        if item["type"] == "mcp_approval_request":
            print("Approval ID:", item["id"])
            print("Review:", json.dumps(item, ensure_ascii=True))
        elif item["type"] == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    print(content["text"])
    if response["status"] == "failed":
        print("Response error:", json.dumps(response.get("error", {})), file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    conversation_path = private_path(args.conversation)
    lock = conversation_path.with_suffix(".lock")
    try:
        lock.touch(exist_ok=False)
    except FileExistsError:
        raise RuntimeError("Another invocation holds this conversation lock; wait rather than replay") from None
    try:
        run(args)
    finally:
        lock.unlink()


if __name__ == "__main__":
    try:
        main()
    except HttpResponseError as error:
        request_id = error.response.headers.get("x-ms-request-id") if error.response else None
        print(f"FAIL: HTTP {error.status_code}; request={request_id}; inspect the pending receipt", file=sys.stderr)
        sys.exit(1)
    except APIStatusError as error:
        print(f"FAIL: HTTP {error.status_code}; request={error.request_id}; inspect the pending receipt and Foundry diagnostics", file=sys.stderr)
        sys.exit(1)
    except (APIConnectionError, APITimeoutError, ValueError, RuntimeError, OSError) as error:
        print(f"FAIL: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)
