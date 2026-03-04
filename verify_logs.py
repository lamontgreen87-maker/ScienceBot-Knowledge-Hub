import json
import os

def check_file(path, label):
    print(f"--- {label} ---")
    if not os.path.exists(path):
        print("File not found.")
        return
    
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            if isinstance(data, list):
                print(f"Total entries: {len(data)}")
                last_items = data[-2:]
                for i, item in enumerate(last_items):
                    print(f"--- Entry -{len(last_items)-i} ---")
                    if label == "Failures Log":
                        print(f"Topic: {item.get('topic')}")
                        print(f"Audit Reason: {item.get('audit_reason')}")
                        print(f"Data Preview: {str(item.get('data'))[:200]}")
                    else:
                        print(f"Topic: {item.get('topic')}")
                        print(f"Summary: {item.get('summary')}")
                    print("-" * 20)
            else:
                print("Data is not a list.")
    except Exception as e:
        print(f"Error reading {path}: {e}")

check_file(r"c:\continuous\memory\failures.json", "Failures Log")
check_file(r"c:\continuous\memory\scientific_journal.json", "Scientific Journal")
