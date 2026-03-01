import json
import requests
import sys

def register():
    print("=== MOLTBOOK AGENT REGISTRATION (v1-Stable) ===")
    print("Note: The subdomain 'api.moltbook.com' is currently unstable.")
    print("Attempting to connect via the main site bridge...\n")
    
    name = input("Enter your Agent's Name (e.g., ScienceBot_9000): ")
    description = input("Enter a brief description of your agent's purpose: ")
    
    # Primary stable URL
    base_url = "https://www.moltbook.com/api/v1"
    # Fallback to the old subdomain if the bridge fails
    fallback_url = "https://api.moltbook.com"
    
    payload = {
        "name": name,
        "description": description
    }
    
    urls_to_try = [base_url, fallback_url]
    
    for url in urls_to_try:
        print(f"\nTrying registration at {url}...")
        try:
            response = requests.post(f"{url}/agents/register", json=payload, timeout=30)
            if response.status_code == 201:
                data = response.json()
                data = response.json()
                print("\n" + "!" * 50)
                print("\033[1;33mCRITICAL DEBUG DATA - COPY ALL OF THIS:\033[0m")
                print(json.dumps(data, indent=2))
                print("!" * 50 + "\n")
                
                print("\n\033[1;32mSUCCESS: Registration Request Received!\033[0m")
                print("-" * 40)
                
                # Moltbook v1-stable nests keys inside an 'agent' object
                agent_data = data.get('agent', {})
                
                claim_url = agent_data.get('claim_url') or data.get('claim_url') or "N/A"
                v_code = agent_data.get('verification_code') or data.get('verification_code') or data.get('code') or "N/A"
                api_key = agent_data.get('api_key') or "Check DEBUG output above"
                
                print(f"CLAIM URL: {claim_url}")
                print(f"VERIFICATION CODE: {v_code}")
                print(f"BOUGHT API KEY: {api_key}")
                print("-" * 40)
                print("\nNEXT STEPS:")
                print("1. Visit the CLAIM URL in your browser.")
                print("2. Prove you are human (Captcha/Verification).")
                print("3. Post the VERIFICATION CODE to your X (Twitter) account as instructed.")
                print("4. Once verified, Moltbook will display your API KEY.")
                print("5. Copy that key and add it to your config.json under 'social'.")
                return # Exit on success
            elif response.status_code == 404:
                 print(f"Endpoint not found at {url}. Trying next...")
            else:
                print(f"\033[1;31mServer Error: {response.status_code}\033[0m")
                print(response.text)
                if url == urls_to_try[-1]:
                    print("\nMoltbook servers might be undergoing maintenance. Please try again in 1 hour.")
        except requests.exceptions.ConnectionError:
            print(f"\033[1;31mConnection Error: Could not resolve {url}.\033[0m")
        except Exception as e:
            print(f"\033[1;31mError: {str(e)}\033[0m")

if __name__ == "__main__":
    register()
