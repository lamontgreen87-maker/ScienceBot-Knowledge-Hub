import json
import re
import jsonschema
from jsonschema import validate

# === SCHEMAS ===

HYPOTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "hypothesis": {"type": "string"},
        "simulation_context": {"type": "string"},
        "literature_grounding": {"type": "string"},
        "physics_primer": {"type": "string"},
        "atomic_specification": {
            "type": "object",
            "properties": {
                "independent_variable": {"type": "object"},
                "dependent_variable": {"type": "object"},
                "symbolic_parameters": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["independent_variable", "dependent_variable", "symbolic_parameters"]
        },
        "mathematical_blueprint": {"type": "string"},
        "mathematical_implementation_guide": {"type": "string"},
        "target_complexity_score": {"type": ["string", "integer"]},
        "required_constants": {"type": "object"}
    },
    "required": [
        "topic", "hypothesis", "physics_primer", 
        "mathematical_blueprint", "mathematical_implementation_guide", 
        "required_constants"
    ],
    "additionalProperties": True
}

BATCH_HYPOTHESES_SCHEMA = {
    "type": "object",
    "properties": {
        "refined_hypotheses": {
            "type": "array",
            "items": HYPOTHESIS_SCHEMA
        }
    },
    "required": ["refined_hypotheses"],
    "additionalProperties": True
}

BATCH_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "audit_reports": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "audit_passed": {"type": "boolean"},
                    "rejection_type": {"type": "string", "enum": ["FIXABLE", "FATAL", "NONE"]},
                    "reasoning": {"type": "string"}
                },
                "required": ["index", "audit_passed", "rejection_type", "reasoning"]
            }
        },
        "collective_insight": {"type": "string"}
    },
    "required": ["audit_reports"],
    "additionalProperties": True
}

AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "audit_passed": {"type": "boolean"},
        "rejection_type": {"type": "string", "enum": ["FIXABLE", "FATAL", "NONE"]},
        "reasoning": {"type": "string"},
        "test_coverage": {"type": "string"},
        "cheat_detected": {"type": "boolean"}
    },
    "required": ["audit_passed", "rejection_type", "reasoning"],
    "additionalProperties": True
}

SCHEMAS = {
    "hypothesis": HYPOTHESIS_SCHEMA,
    "audit": AUDIT_SCHEMA,
    "batch_hypotheses": BATCH_HYPOTHESES_SCHEMA,
    "batch_audit": BATCH_AUDIT_SCHEMA
}

# === UTILITIES ===

def extract_json(response):
    """
    Robustly extracts the first valid JSON object from a string.
    Handles Markdown code blocks, leading/trailing chatter, and brace counting.
    """
    if not response: return None
    
    # 1. Try to find content within Markdown code blocks first
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if code_block_match:
        candidate = code_block_match.group(1).strip()
        try:
            return json.loads(candidate)
        except:
            pass 

    # 2. Brace-counting search for the first valid object or array
    try:
        # Strip BOM if present
        response = response.lstrip('\ufeff').lstrip('\ufffe')
        
        # Find the first potential start of JSON
        start_match = re.search(r'[\{\[]', response)
        if not start_match: return None
        start_idx = start_match.start()
        
        count = 0
        in_string = False
        escaped = False
        
        for i in range(start_idx, len(response)):
            char = response[i]
            
            if char == '"' and not escaped:
                in_string = not in_string
            
            if not in_string:
                if char in '{[':
                    count += 1
                elif char in '}]':
                    count -= 1
                    if count == 0:
                        json_str = response[start_idx:i+1]
                        return json.loads(json_str)
            
            if char == '\\' and not escaped:
                escaped = True
            else:
                escaped = False
                
        return None
    except json.JSONDecodeError as decode_error:
        # Final fallback: Attempt to parse a stripped version of the substring
        # that might have a trailing comma or malformed brace
        try:
            return json.loads(response[start_idx:response.rfind('}')+1])
        except:
            return None
    except Exception:
        return None

def _normalize_hypothesis_item(data):
    """Internal helper to normalize a single hypothesis dictionary."""
    if not isinstance(data, dict):
        return data

    # 1. Normalize required_constants: convert string values to numbers
    constants = data.get("required_constants", {})
    if isinstance(constants, dict):
        new_constants = {}
        for k, v in constants.items():
            if isinstance(v, (int, float)):
                new_constants[k] = v
            elif isinstance(v, str):
                try:
                    v_clean = v.strip().replace(',', '').split()[0]
                    num_match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', v_clean)
                    if num_match:
                        new_constants[k] = float(num_match.group())
                    else:
                        new_constants[k] = v
                except:
                    new_constants[k] = v
            else:
                new_constants[k] = v
        data["required_constants"] = new_constants

    # 2. Ensure atomic_specification has defaults
    if "atomic_specification" not in data:
        data["atomic_specification"] = {
            "independent_variable": {"name": "t", "symbol": "t"},
            "dependent_variable": {"name": "y", "symbol": "y"},
            "symbolic_parameters": ["t", "y"]
        }
    
    # 3. Handle list vs string for symbolic_parameters
    params = data["atomic_specification"].get("symbolic_parameters", [])
    if isinstance(params, str):
        data["atomic_specification"]["symbolic_parameters"] = [p.strip() for p in params.split(',')]

    # 4. Mandatory Blueprint and Implementation Fallback
    if "mathematical_blueprint" not in data or not str(data["mathematical_blueprint"]).strip():
        ind_var = data["atomic_specification"]["independent_variable"]["symbol"]
        dep_var = data["atomic_specification"]["dependent_variable"]["symbol"]
        data["mathematical_blueprint"] = f"constants['ALPHA'] * {dep_var} + constants['BETA'] * {ind_var}"
    
    if "mathematical_implementation_guide" not in data or not str(data["mathematical_implementation_guide"]).strip():
        data["mathematical_implementation_guide"] = "Use a 50-step Rolling Memory Window to evaluate fractional kernels and strictly deplete resource pools."
        
    if not data.get("required_constants"):
        data["required_constants"] = {"ALPHA": 0.5, "BETA": 1.2}
    
    return data

def normalize_data(data, schema_type):
    """
    Ensures data consistency by fixing common LLM formatting errors.
    Recursively repairs batch lists and individual components.
    """
    if not data:
        return data

    # FEATURE 6: Auto-Wrap Raw Lists into Batch Objects
    if isinstance(data, list):
        if schema_type == "batch_hypotheses":
            data = {"refined_hypotheses": data}
        elif schema_type == "batch_audit":
            data = {"audit_reports": data}

    if not isinstance(data, dict):
        return data

    # 1. Normalize Batch Hypotheses
    if schema_type == "batch_hypotheses" and "refined_hypotheses" in data:
        items = data["refined_hypotheses"]
        if isinstance(items, list):
            data["refined_hypotheses"] = [_normalize_hypothesis_item(h) for h in items]

    # 2. Normalize Single Hypothesis
    if schema_type == "hypothesis":
        data = _normalize_hypothesis_item(data)

    return data

def validate_json_schema(data, schema_type):
    """
    Strict validation with descriptive error messages for LLM feedback.
    """
    if schema_type not in SCHEMAS:
        return True, None
        
    try:
        validate(instance=data, schema=SCHEMAS[schema_type])
        return True, None
    except jsonschema.exceptions.ValidationError as e:
        path = " -> ".join([str(p) for p in e.path]) if e.path else "root"
        msg = f"Validation Error at {path}: {e.message}"
        if e.validator == "required":
            msg = f"CRITICAL: {e.message} at path: {path}"
        msg = msg.replace('\n', ' ').replace('\r', '')
        return False, msg

def extract_and_validate(response, schema_type):
    """
    The master entry point for robust JSON handling.
    Extracts, validates against schema, and normalizes.
    Returns (data, error_message).
    """
    data = extract_json(response)
    if not data:
        return None, "Failed to extract valid JSON from response. Ensure you use ```json code blocks and provide a complete object."
        
    # --- FEATURE 5: Aggressive Null Catching ---
    if isinstance(data, dict):
        if len(data.keys()) == 0 or (len(data.keys()) == 1 and list(data.values())[0] == ""):
            return None, "Extracted JSON object was empty or essentially blank."

    # Validate
    success, err = validate_json_schema(data, schema_type)
    if not success:
        # Attempt normalization first, maybe it fixes a type mismatch
        data = normalize_data(data, schema_type)
        success, err = validate_json_schema(data, schema_type)
        if not success:
            # Enhanced feedback: include the specific validation error to help LLM self-fix
            return data, f"JSON Schema Validation Failed: {err}. Please correct the structure and try again."

    # Normalize (Double check after validation)
    data = normalize_data(data, schema_type)
    
    return data, None
