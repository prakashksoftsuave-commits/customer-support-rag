import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rag.agent import SupportReActAgent, AVAILABLE_TOOLS

def test_mcp_integration():
    print("Available tools:", AVAILABLE_TOOLS.keys())
    assert "ticket_history" in AVAILABLE_TOOLS, "ticket_history not discovered"
    print("Tool discovered successfully.")
    
    # Verify we can call the tool
    tool = AVAILABLE_TOOLS["ticket_history"]
    print("Calling ticket_history tool...")
    result = tool["fn"]("T-123")
    print(f"Tool result: {result}")
    assert "Closed" in result, "Unexpected tool result"
    print("Tool executed successfully.")

if __name__ == "__main__":
    test_mcp_integration()
