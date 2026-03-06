with open("agent.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(r'\"\"\"', '\"\"\"')

with open("agent.py", "w", encoding="utf-8") as f:
    f.write(text)
