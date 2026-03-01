import time
import sys
import os

def inject_prompt(prompt):
    mailbox_path = "c:\\continuous\\memory\\interrupt.txt"
    with open(mailbox_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"Prompt injected: {prompt}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inject_prompt(" ".join(sys.argv[1:]))
    else:
        print("Usage: python cli_injector.py \"Your prompt here\"")
