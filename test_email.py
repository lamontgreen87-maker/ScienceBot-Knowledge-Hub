import json
import traceback
from press_office import PressOffice

def main():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")
        return

    # Create dummy discovery
    dummy_discovery = {
        "hypothesis": {
            "topic": "Test Discovery for Notifications",
            "hypothesis": "Test Hypothesis Content"
        },
        "invention": "Test Invention Details",
        "evaluation": "Test Evaluation Details"
    }

    # Initialize Press Office (pass None for UI to print to terminal)
    po = PressOffice(config, ui=None)

    print("Attempting to send test email...")
    # Directly call send_email to avoid querying the LLM
    po.send_email(
        subject="Breakthrough Discovery: Test Discovery for Notifications",
        body="This is a test press release from your Swarm. If you see this, email notifications are fully configured and working!"
    )
    print("Test complete. Check the logs above to see if it succeeded or failed based on your config.json credentials.")

if __name__ == "__main__":
    main()
