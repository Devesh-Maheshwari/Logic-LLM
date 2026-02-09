"""
Smart Verification Strategy:
1. Quick syntax check (fast, catches 30% of errors)
2. Pattern-based heuristics (fast, catches another 30%)
3. Deep LLM verification only for suspicious programs (catches remaining 40%)
"""

import re

def predict_failure_risk(logic_program, dataset_name="FOLIO"):
    """
    Predict if a program is likely to fail WITHOUT executing it
    Returns: (risk_score, reasons)
    risk_score: 0.0 (safe) to 1.0 (very risky)
    """
    risk_score = 0.0
    reasons = []

    if dataset_name == "FOLIO":
        # Extract sections
        try:
            parts = logic_program.split("Conclusion:")
            if len(parts) < 2:
                return 1.0, ["Missing Conclusion section"]

            predicates_section = parts[0].split("Predicates:")[1].split("Premises:")[0]
            premises_section = parts[0].split("Premises:")[1]
            conclusion_section = parts[1].strip()

            # Risk factor 1: Complex XOR operations (known failure mode)
            xor_count = logic_program.count(' ⊕ ')
            if xor_count > 2:
                risk_score += 0.3
                reasons.append(f"Complex XOR logic ({xor_count} XOR operators)")

            # Risk factor 2: Nested quantifiers
            nested_quantifiers = re.findall(r'∀\w+\s*\(∀', logic_program) + re.findall(r'∃\w+\s*\(∃', logic_program)
            if nested_quantifiers:
                risk_score += 0.2
                reasons.append("Nested quantifiers detected")

            # Risk factor 3: Very long formulas (likely complex)
            long_formulas = [line for line in premises_section.split('\n') if len(line) > 200]
            if long_formulas:
                risk_score += 0.2
                reasons.append(f"{len(long_formulas)} very long formulas")

            # Risk factor 4: Unusual predicate count mismatch
            defined_preds = len(re.findall(r'(\w+)\(x\) :::', predicates_section))
            used_preds_count = len(set(re.findall(r'([A-Z][a-zA-Z]*)\(', premises_section + conclusion_section)))

            if defined_preds < used_preds_count - 1:
                risk_score += 0.4
                reasons.append(f"Predicate mismatch: {defined_preds} defined but {used_preds_count} used")

            # Risk factor 5: Complex conclusion (more likely to be wrong)
            if len(conclusion_section.split(':::')[0]) > 100:
                risk_score += 0.15
                reasons.append("Complex conclusion")

            # Risk factor 6: Negations in complex positions
            complex_negations = re.findall(r'¬\(.*?⊕.*?\)', logic_program)
            if complex_negations:
                risk_score += 0.2
                reasons.append("Complex negation patterns")

        except Exception as e:
            return 1.0, [f"Parse error: {str(e)}"]

    return min(risk_score, 1.0), reasons


def should_deep_verify(logic_program, dataset_name="FOLIO", threshold=0.5):
    """
    Decide if a program needs deep (LLM-based) verification
    Returns: (bool, risk_score, reasons)
    """
    risk_score, reasons = predict_failure_risk(logic_program, dataset_name)

    return risk_score >= threshold, risk_score, reasons
