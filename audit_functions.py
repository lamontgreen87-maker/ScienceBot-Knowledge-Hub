"""
Deterministic audit functions to validate scientific code before LLM review.
"""
import re
import ast

def validate_template_compliance(code):
    """Checks if the 5-part skeleton sections exist as comments."""
    required_sections = [
        "1. SYMBOLIC SETUP",
        "2. CONSTANT INJECTION",
        "3. THE IMMUTABLE LAW",
        "4. HIGH-FIDELITY EXECUTION",
        "5. DATA LOGGING"
    ]
    missing = [section for section in required_sections if section.lower() not in code.lower()]
    return len(missing) == 0, missing

def validate_constant_injection(code, hypothesis):
    """
    Checks if the 'constants' dictionary exists and contains the required keys.
    """
    required_constants = hypothesis.get('required_constants', {})
    if not required_constants:
        return True, []

    # Look for constants = { ... }
    match = re.search(r'constants\s*=\s*\{([^}]*)\}', code, re.DOTALL)
    if not match:
        return False, ["Missing 'constants = { ... }' dictionary."]

    content = match.group(1)
    missing_keys = []
    for k in required_constants.keys():
        if k not in content:
            missing_keys.append(k)
    
    if missing_keys:
        return False, [f"Missing constants in dict: {', '.join(missing_keys)}"]
    
    return True, []

def check_banned_patterns(code):
    """Enforces absolute prohibitions on negative-evidence behaviors."""
    issues = []
    
    # 1. Banned .subs() block
    if ".subs(" in code:
        issues.append("Forbidden '.subs()' operation detected. Use lambdify/lambda or the approved skeleton.")
            
    return issues

def calculate_vocabulary_alignment(code, hypothesis_text):
    """Calculates what percentage of hypothesis technical words are in the code."""
    hypothesis_text = str(hypothesis_text)
    words = re.findall(r'\b[a-zA-Z]{5,}\b', hypothesis_text.lower())
    if not words:
        return 1.0 # No technical words to match
    
    unique_words = set(words)
    matches = [w for w in unique_words if w in code.lower()]
    score = len(matches) / len(unique_words)
    return score

def get_preflight_report(code, hypothesis):
    """Aggregates all deterministic checks."""
    report = []
    
    temp_ok, missing_sections = validate_template_compliance(code)
    if not temp_ok:
        report.append(f"Missing Template Sections: {', '.join(missing_sections)}")
        
    const_ok, missing_consts = validate_constant_injection(code, hypothesis)
    if not const_ok:
        report.extend(missing_consts)
        
    banned_issues = check_banned_patterns(code)
    report.extend(banned_issues)
    
    vocab_score = calculate_vocabulary_alignment(code, hypothesis.get('hypothesis', ''))
    if vocab_score < 0.05:
        report.append(f"Low Vocabulary Alignment ({vocab_score:.1%}). Code must use technical terms from hypothesis.")
        
    return report
