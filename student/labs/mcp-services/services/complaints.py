from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastmcp.exceptions import ToolError
from pydantic import Field

from .common import Limit, Offset, Store, Version, http_app, server
from .fixtures import complaints
from .models import Category, Complaint, ComplaintInput, ComplaintPatch, Description, Event, Identifier, Note, Priority, Specialty, Status, Text, TransactionType

store = Store(complaints())
mcp = server("Musical instrument customer complaints")
TRANSITIONS = {
    "new": {"triaged"},
    "triaged": {"in_progress"},
    "in_progress": {"awaiting_customer", "resolved"},
    "awaiting_customer": {"in_progress", "resolved"},
    "resolved": {"closed", "in_progress"},
    "closed": {"triaged"},
}


@mcp.tool(annotations={"readOnlyHint": True})
def get_complaint(complaint_id: Identifier) -> Complaint:
    """Get a synthetic complaint including notes, transition history and current version."""
    return store.get(complaint_id)


@mcp.tool(annotations={"readOnlyHint": True})
def list_complaints(offset: Offset = 0, limit: Limit = 25) -> dict:
    """List complaints by ID. Follow next_offset until null."""
    with store.lock:
        return store.page(list(store.rows.values()), offset, limit)


@mcp.tool(annotations={"readOnlyHint": True})
def search_complaints(
    query: Annotated[str, Field(max_length=200)] = "",
    status: Status | None = None, priority: Priority | None = None,
    category: Category | None = None,
    instrument_family: Specialty | None = None,
    transaction_type: TransactionType | None = None,
    instrument_serial: Annotated[str | None, Field(max_length=200)] = None,
    country_code: Annotated[str | None, Field(pattern=r"^[A-Z]{2}$")] = None,
    partner_id: Identifier | None = None,
    customer_email: Annotated[str | None, Field(max_length=200)] = None,
    overdue_only: bool = False, offset: Offset = 0, limit: Limit = 25,
) -> dict:
    """Find purchase, repair, rental and warranty complaints with AND filters. Text matches subject, description, customer, instrument/model, serial and order. Overdue excludes resolved/closed cases."""
    now = datetime.now(timezone.utc)
    with store.lock:
        rows = [c for c in store.rows.values()
                if (not query or query.casefold() in " ".join([c.subject, c.description, c.customer.name, c.product, c.instrument_serial or "", c.order_reference]).casefold())
                and (status is None or c.status == status) and (priority is None or c.priority == priority)
                and (category is None or c.category == category)
                and (instrument_family is None or c.instrument_family == instrument_family)
                and (transaction_type is None or c.transaction_type == transaction_type)
                and (instrument_serial is None or (c.instrument_serial or "").casefold() == instrument_serial.casefold())
                and (country_code is None or c.customer.country_code == country_code)
                and (partner_id is None or c.assigned_partner_id == partner_id)
                and (customer_email is None or c.customer.email.casefold() == customer_email.casefold())
                and (not overdue_only or c.due_at < now and c.status not in {"resolved", "closed"})]
        return store.page(rows, offset, limit)


def save(row: Complaint) -> Complaint:
    row.version += 1
    row.updated_at = datetime.now(timezone.utc)
    store.rows[row.id] = row
    return row.model_copy(deep=True)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def create_complaint(complaint: ComplaintInput) -> Complaint:
    """Create a new complaint; high/critical cases are due in one day, other cases in three."""
    with store.lock:
        if len(store.rows) >= 2000:
            raise ToolError("Demo capacity reached (2000 complaints); delete test records or restart")
        now = datetime.now(timezone.utc)
        row = Complaint(**complaint.model_dump(), id=f"complaint-{uuid4().hex}", version=1,
                        created_at=now, updated_at=now,
                        due_at=now + timedelta(days=1 if complaint.priority in {"high", "critical"} else 3))
        store.rows[row.id] = row
        return row.model_copy(deep=True)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
def update_complaint(complaint_id: Identifier, patch: ComplaintPatch, expected_version: Version) -> Complaint:
    """Change selected case fields, not lifecycle status. Explicit null fields are rejected."""
    with store.lock:
        row = store.check(complaint_id, expected_version)
        changes = patch.model_dump(exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise ToolError("Provide at least one non-null patch field")
        for key, value in changes.items():
            setattr(row, key, value)
        if "priority" in changes:
            row.due_at = row.created_at + timedelta(days=1 if row.priority in {"high", "critical"} else 3)
        return save(row)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def assign_complaint(complaint_id: Identifier, partner_id: Identifier, agent: Text, expected_version: Version) -> Complaint:
    """Assign a partner reference and case owner. First verify the partner is active and supports the instrument family and required sales/repair/rental service using Partner MCP."""
    with store.lock:
        row = store.check(complaint_id, expected_version)
        if row.status in {"resolved", "closed"}:
            raise ToolError("Reopen the complaint before changing its assignment")
        row.assigned_partner_id = partner_id
        row.assigned_agent = agent
        return save(row)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def add_complaint_note(complaint_id: Identifier, author: Text, text: Description, expected_version: Version) -> Complaint:
    """Append a timestamped note without changing status. Maximum 100 notes per case."""
    with store.lock:
        row = store.check(complaint_id, expected_version)
        if len(row.notes) >= 100:
            raise ToolError("Note capacity reached (100)")
        row.notes.append(Note(author=author, text=text, created_at=datetime.now(timezone.utc)))
        return save(row)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
def transition_complaint(
    complaint_id: Identifier, status: Status, reason: Description,
    expected_version: Version, resolution: Description | None = None,
) -> Complaint:
    """Move through new -> triaged -> in_progress -> awaiting_customer/resolved -> closed. Resolved can reopen to in_progress; closed to triaged. Resolving requires resolution."""
    with store.lock:
        row = store.check(complaint_id, expected_version)
        if status not in TRANSITIONS[row.status]:
            raise ToolError(f"Invalid transition {row.status} -> {status}; allowed: {', '.join(sorted(TRANSITIONS[row.status]))}")
        if status == "resolved" and not resolution:
            raise ToolError("A resolution is required")
        if resolution is not None and status != "resolved":
            raise ToolError("Supply resolution only when resolving")
        if len(row.history) >= 100:
            raise ToolError("Transition capacity reached (100)")
        row.history.append(Event(from_status=row.status, to_status=status, reason=reason,
                                 created_at=datetime.now(timezone.utc)))
        row.status = status
        if status == "resolved":
            row.resolution = resolution
        elif status not in {"resolved", "closed"}:
            row.resolution = None
        return save(row)


@mcp.tool(annotations={"readOnlyHint": True})
def complaint_statistics() -> dict:
    """Return case counts by status, priority, category, instrument family and transaction type, including open/overdue totals."""
    with store.lock:
        rows = list(store.rows.values())
        open_rows = [c for c in rows if c.status not in {"resolved", "closed"}]
        return {"total": len(rows), "open": len(open_rows),
                "overdue": sum(c.due_at < datetime.now(timezone.utc) for c in open_rows),
                "by_status": dict(Counter(c.status for c in rows)),
                "by_priority": dict(Counter(c.priority for c in rows)),
                "by_category": dict(Counter(c.category for c in rows)),
                "by_instrument_family": dict(Counter(c.instrument_family for c in rows)),
                "by_transaction_type": dict(Counter(c.transaction_type for c in rows))}


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
def delete_complaint(complaint_id: Identifier, expected_version: Version) -> dict:
    """Delete exactly one synthetic complaint, including its notes/history, using its current version."""
    return store.delete(complaint_id, expected_version)


app = http_app(mcp)
