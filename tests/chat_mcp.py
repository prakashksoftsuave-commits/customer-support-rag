import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rag.agent import SupportReActAgent

def main():
    print("========================================")
    print("🤖 Agent + MCP Interactive Tester")
    print("========================================")
    print("Type a question for the agent. Try asking about ticket 'T-123' or 'T-456'")
    print("to force it to use the new MCP ticket_history tool.")
    print("Type 'exit' to quit.\n")

    agent = SupportReActAgent()

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.strip().lower() in ['exit', 'quit']:
                break
            if not user_input.strip():
                continue
            
            print("\nAgent is thinking...\n")
            result = agent.solve(user_input)
            
            print("--- AGENT REASONING STEPS ---")
            for step in result.steps:
                print(f"\nStep {step.step_num}:")
                if step.thought:
                    print(f"🤔 Thought: {step.thought}")
                if step.action:
                    print(f"🛠️ Tool Used: {step.action} (Input: {step.action_input})")
                if step.observation:
                    print(f"👀 Tool Result: {step.observation}")
                
            print("\n--- FINAL ANSWER ---")
            print(result.final_answer)
            print("----------------------------------------")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nError: {e}")
            break

if __name__ == "__main__":
    main()
