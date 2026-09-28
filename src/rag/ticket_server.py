from mcp.server.mcpserver import MCPServer

# Create an MCP server
mcp = MCPServer("Ticket History Server")

MOCK_TICKET_HISTORY = {
    "T-123": "Ticket T-123 created on 2023-10-01. Issue: Cannot login. Status: Closed.",
    "T-456": "Ticket T-456 created on 2023-11-05. Issue: Sync failed. Status: Open."
}

@mcp.tool()
def ticket_history(ticket_id: str) -> str:
    """Get the history and status of a customer support ticket."""
    return MOCK_TICKET_HISTORY.get(ticket_id.upper(), "Ticket not found.")

@mcp.tool()
def calculate_refund(query: str) -> str:
    """Calculate the pro-rated refund amount. Provide months unused and rate (e.g. '2 months, 15.0 rate')."""
    return f"Calculated Refund: Processed for '{query}'"

@mcp.tool()
def escalate_ticket(ticket_and_reason: str) -> str:
    """Escalate a ticket to Tier 2 engineering. Input the ticket ID and reason."""
    return f"Success: Escalated based on '{ticket_and_reason}'"

if __name__ == "__main__":
    mcp.run()
