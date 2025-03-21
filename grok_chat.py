import asyncio
import sys
from grok_interface import GrokInterface

async def chat_with_grok():
    """Main function to handle chatting with Grok via the interface."""
    interface = GrokInterface()
    
    try:
        print("Connecting to Grok...")
        interface.connect()
        print("Connected successfully! Type your message below (or 'exit'/'quit' to quit).")
        
        while True:
            message = input("You: ").strip()
            
            if message.lower() in ["exit", "quit"]:
                print("Exiting chat...")
                break
            
            if not message:
                print("Please enter a message.")
                continue
            
            print("Sending message...")
            interface.send_message(message)
            
            print("Grok: ", end="", flush=True)
            async for response in interface.receive_message():
                # Add an extra newline after each paragraph for better readability
                print(response, end="\n", flush=True)  # Extra newline for spacing
            print()  # Final newline after the complete response
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        interface.close()
        print("Connection closed.")

def main():
    """Run the async chat function."""
    try:
        asyncio.run(chat_with_grok())
    except KeyboardInterrupt:
        print("\nChat interrupted by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()