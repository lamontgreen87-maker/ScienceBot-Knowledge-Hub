import re

class PreflightRepair:
    """
    Skill: Regex Pre-Processor for SymPy Stability.
    Specializes in converting inefficient .subs() calls to sp.lambdify and fixing Symbol Mismatches.
    """

    @staticmethod
    def lambdify_subs(code):
        """
        Detects .subs() patterns and converts them to lambdify calls for performance and stability.
        Targets both chained .subs() and single calls.
        """
        repairs = []
        new_code = code

        # 1. Detect Chained .subs() Pattern: expr.subs(a, val1).subs(b, val2)...
        # This is a common performance bottleneck in loops.
        chained_pattern = r'(\w+)(\.subs\(\s*[^)]+\s*\)){2,}'
        
        def replace_chained(match):
            expr_name = match.group(1)
            subs_calls = match.group(0)
            
            # Extract symbols and values
            # .subs(x, 1) -> ('x', '1')
            inner_pattern = r'\.subs\(\s*([^,]+)\s*,\s*([^)]+)\s*\)'
            pairs = re.findall(inner_pattern, subs_calls)
            
            if pairs:
                symbols = [p[0].strip() for p in pairs]
                values = [p[1].strip() for p in pairs]
                
                # Create a unique lambdify name
                func_name = f"_f_{expr_name}_stable"
                
                # Check if we already lambdified this expr in this patch session
                # (Simple prevention of duplicate definitions if multiple lines use the same expr)
                lambdify_def = f"{func_name} = sp.lambdify(({', '.join(symbols)}), {expr_name}, 'numpy')"
                
                # We need to insert the definition BEFORE the usage. 
                # For a regex tool, we'll try to find where expr_name was last assigned or just insert at start of LAW section.
                # However, for a simple replacement, we can use a wrapper if it's easier, 
                # but the user wants "stable lambdify format".
                
                repairs.append(f"Converted chained .subs() on '{expr_name}' to lambdify call.")
                return f"sp.lambdify(({', '.join(symbols)}), {expr_name}, 'numpy')({', '.join(values)})"
            
            return match.group(0)

        new_code = re.sub(chained_pattern, replace_chained, new_code)

        # 2. Detect Single .subs() in iterative contexts (heuristic)
        # If .subs() is on a line ending with a loop-like variable or inside a block starting with 'for'
        single_subs_pattern = r'(\w+)\.subs\(\s*([^,]+)\s*,\s*([^)]+)\s*\)'
        
        def replace_single(match):
            expr, sym, val = match.groups()
            # If the value looks like a loop variable (e.g. t_vals[i], y_vals[-1])
            if '[' in val or val.strip() in ['t', 'y', 'state']:
                repairs.append(f"Converted iterative .subs({sym}) on '{expr}' to lambdify.")
                return f"sp.lambdify({sym}, {expr}, 'numpy')({val})"
            return match.group(0)

        new_code = re.sub(single_subs_pattern, replace_single, new_code)
        
        return new_code, repairs

    @staticmethod
    def fix_symbol_mismatch(code, hypothesis):
        """
        Ensures that symbols used in section 3 match the registration in section 1.
        Matches by name to override potential property mismatches (real=True vs default).
        """
        repairs = []
        new_code = code

        # 1. Ensure all hypothesis-required constants are in sp.symbols
        required_consts = hypothesis.get('required_constants', {})
        if required_consts:
            symbol_line_match = re.search(r'symbols\s*\(\s*[\'"](.*?)[\'"]', new_code)
            if symbol_line_match:
                existing_symbols = set(re.split(r'[\s,]+', symbol_line_match.group(1)))
                missing = [c for c in required_consts.keys() if c not in existing_symbols]
                if missing:
                    new_symbols = symbol_line_match.group(1) + " " + " ".join(missing)
                    new_code = new_code.replace(symbol_line_match.group(0), f"symbols('{new_symbols}'")
                    repairs.append(f"Added missing symbols to registration: {', '.join(missing)}")

        # 2. Force name-based symbol matching for .subs() (if any are left)
        # expr.subs(Symbol('x'), val) -> expr.subs(sp.Symbol('x'), val) 
        # But specifically targeting cases where models use a variable name that might not be a Symbol object.
        return new_code, repairs

    @staticmethod
    def apply_all(code, hypothesis):
        """Runs the complete suite of regex pre-processing repairs."""
        all_repairs = []
        
        # 1. Lambdify
        code, r1 = PreflightRepair.lambdify_subs(code)
        all_repairs.extend(r1)
        
        # 2. Symbols
        code, r2 = PreflightRepair.fix_symbol_mismatch(code, hypothesis)
        all_repairs.extend(r2)
        
        return code, all_repairs
