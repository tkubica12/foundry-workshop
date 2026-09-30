from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastmcp.exceptions import ToolError
from pydantic import Field

from .common import Limit, Offset, Store, Version, http_app, server
from .fixtures import partners
from .models import Identifier, Partner, PartnerInput

store = Store(partners())
mcp = server("Authorized service partners")


@mcp.tool(annotations={"readOnlyHint": True})
def get_partner(partner_id: Identifier) -> Partner:
    """Get one synthetic partner, including its version for safe updates."""
    return store.get(partner_id)


@mcp.tool(annotations={"readOnlyHint": True})
def list_partners(offset: Offset = 0, limit: Limit = 25) -> dict:
    """List partners ordered by ID. Follow next_offset until null."""
    with store.lock:
        return store.page(list(store.rows.values()), offset, limit)


@mcp.tool(annotations={"readOnlyHint": True})
def search_partners(
    query: Annotated[str, Field(max_length=200)] = "",
    country_code: Annotated[str | None, Field(pattern=r"^[A-Z]{2}$")] = None,
    city: Annotated[str | None, Field(max_length=200)] = None,
    status: Literal["active", "suspended", "pending"] | None = None,
    tier: Literal["standard", "silver", "gold", "platinum"] | None = None,
    specialty: Literal["hvac", "appliances", "solar", "electrical", "plumbing"] | None = None,
    language: Annotated[str | None, Field(max_length=200)] = None,
    emergency_service: bool | None = None,
    min_rating: Annotated[float, Field(ge=0, le=5)] = 0,
    min_capacity: Annotated[int, Field(ge=0, le=500)] = 0,
    offset: Offset = 0, limit: Limit = 25,
) -> dict:
    """Search with AND filters. Text matches name, city, street, contact and certification, case-insensitively."""
    with store.lock:
        rows = [p for p in store.rows.values()
                if (not query or query.casefold() in " ".join([p.name, p.address.city, p.address.street, p.contact_name, *p.certifications]).casefold())
                and (country_code is None or p.address.country_code == country_code)
                and (city is None or city.casefold() in p.address.city.casefold())
                and (status is None or p.status == status) and (tier is None or p.tier == tier)
                and (specialty is None or specialty in p.specialties)
                and (language is None or language.casefold() in [s.casefold() for s in p.languages])
                and (emergency_service is None or p.emergency_service == emergency_service)
                and p.rating >= min_rating and p.capacity_per_week >= min_capacity]
        return store.page(rows, offset, limit)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False})
def create_partner(partner: PartnerInput) -> Partner:
    """POST semantics: create a partner with a server-generated unique ID."""
    with store.lock:
        if len(store.rows) >= 2000:
            raise ToolError("Demo capacity reached (2000 partners); delete test records or restart")
        row = Partner(**partner.model_dump(), id=f"partner-{uuid4().hex}", version=1,
                      updated_at=datetime.now(timezone.utc))
        store.rows[row.id] = row
        return row.model_copy(deep=True)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True})
def put_partner(partner_id: Identifier, partner: PartnerInput, expected_version: Version | None = None) -> Partner:
    """PUT semantics: create at an unused ID without a version, or replace an existing record with its current version."""
    with store.lock:
        exists = partner_id in store.rows
        if exists:
            if expected_version is None:
                raise ToolError("expected_version is required to replace an existing partner")
            previous = store.check(partner_id, expected_version)
            if previous.model_dump(include=set(PartnerInput.model_fields)) == partner.model_dump():
                return previous
        elif expected_version is not None:
            raise ToolError(f"Not found: {partner_id}; omit expected_version to create")
        elif len(store.rows) >= 2000:
            raise ToolError("Demo capacity reached (2000 partners)")
        row = Partner(**partner.model_dump(), id=partner_id, version=previous.version + 1 if exists else 1,
                      updated_at=datetime.now(timezone.utc))
        store.rows[partner_id] = row
        return row.model_copy(deep=True)


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True})
def delete_partner(partner_id: Identifier, expected_version: Version) -> dict:
    """Delete exactly one synthetic partner using its current version; does not change complaints."""
    return store.delete(partner_id, expected_version)


app = http_app(mcp)
