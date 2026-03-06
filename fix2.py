with open("agent.py", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    'f"CRITICAL CROSS-POLLINATION MANDATE:\n"\n                                    f"You MUST use this exact hybrid hypothesis as your foundation for the new field: {cross_pollinated[\'hybrid_hypothesis\']}\n"\n                                    f"Context: {cross_pollinated[\'isomorphism_analysis\']}"',
    'f"CRITICAL CROSS-POLLINATION MANDATE:\\n"\\\n                                    f"You MUST use this exact hybrid hypothesis as your foundation for the new field: {cross_pollinated[\'hybrid_hypothesis\']}\\n"\\\n                                    f"Context: {cross_pollinated[\'isomorphism_analysis\']}"'
)

c = c.replace(
    'f"## [DREAM PHASE ADVICE] {time.strftime(\'%Y-%m-%d %H:%M:%S\')}\n{ds_dream}\n"\n                        )',
    'f"## [DREAM PHASE ADVICE] {time.strftime(\'%Y-%m-%d %H:%M:%S\')}\\n{ds_dream}\\n"\n                        )'
)

with open("agent.py", "w", encoding="utf-8") as f:
    f.write(c)
