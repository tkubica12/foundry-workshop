"""Check an already running offline fixture through real Responses HTTP."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post(data):
    with urlopen(Request("http://127.0.0.1:8088/responses", json.dumps(data).encode(),
                         {"Content-Type": "application/json"}), timeout=60) as response:
        return json.load(response)


def main():
    for _ in range(60):
        try:
            with urlopen("http://127.0.0.1:8088/readiness", timeout=2) as response:
                assert response.status == 200
            break
        except (HTTPError, URLError, TimeoutError):
            time.sleep(1)
    else:
        raise RuntimeError("Protocol fixture never became ready")
    pending = post({"input": "Read the fixture partner", "stream": False})
    approvals = [item for item in pending["output"] if item["type"] == "mcp_approval_request"]
    assert len(approvals) == 1, pending
    result = post({
        "previous_response_id": pending["id"],
        "input": [{"type": "mcp_approval_response", "approval_request_id": approvals[0]["id"], "approve": True}],
        "stream": False,
    })
    assert result["status"] == "completed", result
    assert "fixture-partner-001" in json.dumps(result["output"]), result
    denied_pending = post({"input": "Read again", "stream": False})
    approval = next(item for item in denied_pending["output"] if item["type"] == "mcp_approval_request")
    denied = post({
        "previous_response_id": denied_pending["id"],
        "input": [{"type": "mcp_approval_response", "approval_request_id": approval["id"], "approve": False}],
        "stream": False,
    })
    assert denied["status"] == "failed" and denied["error"]["code"] == "interrupt_rejected", denied
    print("PASS: readiness, Responses approval continuation, answer and explicit rejection (offline fixture)")


if __name__ == "__main__":
    main()
