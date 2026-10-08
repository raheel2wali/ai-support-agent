"""Tools the agent can call.

These are stand-ins with fake data so the whole loop can be tested
end to end. In production, order_lookup hits your order system and
create_ticket hits your helpdesk API — same signatures.
"""

# Fake order DB. Replace with a real query.
ORDERS = {
    "1042": {"status": "shipped", "eta": "Oct 12", "carrier": "TCS"},
    "1043": {"status": "processing", "eta": "Oct 14", "carrier": "Leopards"},
    "1044": {"status": "delivered", "eta": "Oct 6", "carrier": "TCS"},
}


def order_lookup(order_id: str) -> dict:
    """Look up an order by ID. Returns status info or an error dict."""
    order_id = order_id.strip().lstrip("#")
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"no order found with id {order_id}"}
    return {"order_id": order_id, **order}


# In-memory ticket store. Swap for your helpdesk API.
_tickets: list[dict] = []


def create_ticket(subject: str, description: str, customer: str) -> dict:
    """Open a support ticket. Returns the ticket id."""
    ticket_id = f"T-{1000 + len(_tickets)}"
    _tickets.append(
        {
            "id": ticket_id,
            "subject": subject,
            "description": description,
            "customer": customer,
            "status": "open",
        }
    )
    return {"ticket_id": ticket_id, "status": "open"}


# JSON schemas handed to the model for function calling.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "order_lookup",
            "description": "Look up an order's shipping status by order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order number, e.g. 1042"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Open a support ticket for issues the agent can't resolve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "description": {"type": "string"},
                    "customer": {"type": "string", "description": "Customer identifier"},
                },
                "required": ["subject", "description", "customer"],
            },
        },
    },
]

IMPLEMENTATIONS = {
    "order_lookup": order_lookup,
    "create_ticket": create_ticket,
}
