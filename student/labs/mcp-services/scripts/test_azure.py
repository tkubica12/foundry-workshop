"""Safe mocked regression checks; never invokes Azure or reads the API key."""
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import azure

SUB = "00000000-0000-0000-0000-000000000000"
SCOPE = f"/subscriptions/{SUB}/resourceGroups/rg-unit-test"
ENV_ID = f"{SCOPE}/providers/Microsoft.App/managedEnvironments/{azure.ENVIRONMENT}"


def args(action="cleanup"):
    return Namespace(action=action, subscription=SUB, resource_group="rg-unit-test",
                     location="swedencentral", confirm=True)


class FakeAzure:
    def __init__(self, foreign_on_second_page=True, foreign_host=False, unowned=False):
        self.calls = []
        self.foreign = foreign_on_second_page
        self.foreign_host = foreign_host
        self.unowned = unowned

    def request(self, method, path, body=None, missing=False):
        self.calls.append((method, path))
        if method == "DELETE":
            return {}
        if path == SCOPE:
            return {"tags": {"purpose": azure.PURPOSE}}
        if path == ENV_ID:
            return {"tags": {"purpose": azure.PURPOSE}, "properties": {"environmentMode": "Express"}}
        if path.endswith("/containerApps"):
            return {"value": [], "nextLink": "https://untrusted.example/page2" if self.foreign_host else
                    f"https://management.azure.com{SCOPE}/providers/Microsoft.App/containerApps?api-version={azure.API}&page=2"}
        if "page=2" in path:
            return {"value": [{"id": SCOPE + "/providers/Microsoft.App/containerApps/foreign",
                              "properties": {"environmentId": ENV_ID}}] if self.foreign else []}
        return {"tags": {"purpose": "unrelated" if self.unowned else azure.PURPOSE}}

    def wait(self, path, absent=False):
        self.calls.append(("WAIT", path))


class CleanupTests(unittest.TestCase):
    def execute(self, fake, operation):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(azure, "STATE", Path(directory) / "state.json"), \
                patch.object(azure, "az", return_value={"id": SUB}), \
                patch.object(azure, "Azure", return_value=fake):
            operation()

    def test_foreign_app_on_second_page_blocks_every_delete(self):
        fake = FakeAzure()
        def operation():
            with self.assertRaisesRegex(RuntimeError, "unrelated apps"):
                azure.run(args())
        self.execute(fake, operation)
        self.assertFalse(any(method == "DELETE" for method, _ in fake.calls))
        self.assertTrue(any("page=2" in path for _, path in fake.calls))

    def test_cleanup_deletes_only_two_apps_and_environment(self):
        fake = FakeAzure(foreign_on_second_page=False)
        self.execute(fake, lambda: azure.run(args()))
        deleted = [path for method, path in fake.calls if method == "DELETE"]
        self.assertEqual(len(deleted), 3)
        self.assertNotIn(SCOPE, deleted)
        self.assertEqual(deleted[-1], ENV_ID)

    def test_unowned_app_blocks_cleanup(self):
        fake = FakeAzure(unowned=True)
        def operation():
            with self.assertRaisesRegex(RuntimeError, "unowned resource"):
                azure.run(args())
        self.execute(fake, operation)
        self.assertFalse(any(method == "DELETE" for method, _ in fake.calls))

    def test_cleanup_requires_confirmation(self):
        fake = FakeAzure()
        request = args()
        request.confirm = False
        def operation():
            with self.assertRaisesRegex(ValueError, "requires --confirm"):
                azure.run(request)
        self.execute(fake, operation)
        self.assertFalse(any(method == "DELETE" for method, _ in fake.calls))

    def test_http_pagination_cannot_send_token_to_another_host(self):
        client = object.__new__(azure.Azure)
        client.token = "synthetic-unit-token"
        with patch.object(azure, "urlopen") as open_url:
            with self.assertRaisesRegex(RuntimeError, "outside the management endpoint"):
                client.request("GET", "https://untrusted.example/page2")
            open_url.assert_not_called()

    def test_recovery_marker_retained_on_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(azure, "LOCK", Path(directory) / "lock"):
            with self.assertRaisesRegex(RuntimeError, "failure"):
                with azure.operation_lock():
                    raise RuntimeError("failure")
            self.assertTrue(azure.LOCK.exists())
            with self.assertRaisesRegex(RuntimeError, "recovery marker"):
                with azure.operation_lock():
                    pass

    def test_success_removes_marker(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(azure, "LOCK", Path(directory) / "lock"):
            with azure.operation_lock():
                self.assertTrue(azure.LOCK.exists())
            self.assertFalse(azure.LOCK.exists())


if __name__ == "__main__":
    unittest.main()
