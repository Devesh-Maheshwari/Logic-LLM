"""
Pre-Execution Verification Module
Catches syntax and semantic errors BEFORE solver execution
"""

import re
from utils import OpenAIModel

class LogicProgramVerifier:
    def __init__(self, api_key, model_name="gpt-4", max_tokens=512):
        self.llm = OpenAIModel(api_key, model_name, stop_words=[], max_new_tokens=max_tokens)

    def verify_program(self, logic_program, dataset_name="FOLIO"):
        """
        Verify logic program for syntax and semantic errors
        Returns: (is_valid, error_messages, confidence)
        """
        if dataset_name == "FOLIO":
            return self._verify_fol_program(logic_program)
        else:
            # For other datasets, skip verification for now
            return True, [], 1.0

    def _verify_fol_program(self, logic_program):
        """Verify First-Order Logic program (FOLIO)"""
        errors = []

        # Quick structural checks
        if "Predicates:" not in logic_program:
            errors.append("Missing Predicates section")
        if "Premises:" not in logic_program:
            errors.append("Missing Premises section")
        if "Conclusion:" not in logic_program:
            errors.append("Missing Conclusion section")

        if errors:
            return False, errors, 0.0

        # Extract sections
        try:
            predicates_section = logic_program.split("Premises:")[0].split("Predicates:")[1].strip()
            premises_section = logic_program.split("Conclusion:")[0].split("Premises:")[1].strip()
            conclusion_section = logic_program.split("Conclusion:")[1].strip()
        except:
            return False, ["Failed to parse program sections"], 0.0

        # Check 1: Extract defined predicates
        defined_predicates = set()
        for line in predicates_section.split('\n'):
            if ':::' in line:
                pred_name = line.split('(')[0].strip()
                if pred_name:
                    defined_predicates.add(pred_name)

        # Check 2: Find all used predicates in premises and conclusion
        used_predicates = set()
        for line in (premises_section + '\n' + conclusion_section).split('\n'):
            if ':::' in line:
                formula = line.split(':::')[0].strip()
                # Extract predicate names (capitalized words followed by '(')
                found_preds = re.findall(r'([A-Z][a-zA-Z]*)\(', formula)
                used_predicates.update(found_preds)

        # Check 3: Undefined predicates
        undefined = used_predicates - defined_predicates
        if undefined:
            errors.append(f"Undefined predicates: {', '.join(undefined)}")

        # Check 4: Parentheses balance
        full_formulas = premises_section + conclusion_section
        if full_formulas.count('(') != full_formulas.count(')'):
            errors.append("Unbalanced parentheses in formulas")

        # Check 5: Common syntax errors
        if '∀x∀' in logic_program or '∃x∃' in logic_program:
            errors.append("Missing space between quantifiers")

        # If errors found, return them
        if errors:
            return False, errors, 0.3

        # All checks passed
        return True, [], 1.0

    def fix_program(self, logic_program, errors, dataset_name="FOLIO"):
        """
        Attempt to fix identified errors
        Returns: (fixed_program, success)
        """
        prompt = self._create_fix_prompt(logic_program, errors, dataset_name)

        try:
            fixed_program = self.llm.generate(prompt).strip()

            # Verify the fix didn't make things worse
            is_valid, new_errors, _ = self.verify_program(fixed_program, dataset_name)

            if is_valid or len(new_errors) < len(errors):
                return fixed_program, True
            else:
                # Fix made it worse, return original
                return logic_program, False
        except:
            return logic_program, False

    def _create_fix_prompt(self, logic_program, errors, dataset_name):
        """Create prompt for fixing errors"""

        error_list = "\n".join([f"- {err}" for err in errors])

        prompt = f"""The following {dataset_name} logic program has errors. Please fix them.

LOGIC PROGRAM:
{logic_program}

ERRORS FOUND:
{error_list}

INSTRUCTIONS:
1. Fix ONLY the identified errors
2. Keep all other parts unchanged
3. Ensure all predicates used are defined
4. Check parentheses are balanced
5. Maintain the same logical meaning

OUTPUT THE CORRECTED PROGRAM ONLY (no explanations):
"""
        return prompt

    def smart_verify_and_fix(self, logic_program, dataset_name="FOLIO", max_attempts=2):
        """
        Verify and fix program with multiple attempts if needed
        Returns: (final_program, was_fixed, is_valid)
        """
        # First verification
        is_valid, errors, confidence = self.verify_program(logic_program, dataset_name)

        if is_valid:
            return logic_program, False, True

        # Try to fix
        attempts = 0
        current_program = logic_program

        while attempts < max_attempts and not is_valid:
            fixed_program, fix_success = self.fix_program(current_program, errors, dataset_name)

            if not fix_success:
                # Fix failed, return best attempt
                return current_program, attempts > 0, False

            # Verify the fix
            is_valid, errors, confidence = self.verify_program(fixed_program, dataset_name)
            current_program = fixed_program
            attempts += 1

            if is_valid:
                return current_program, True, True

        # Max attempts reached, return last version
        return current_program, attempts > 0, is_valid


def quick_syntax_check(logic_program, dataset_name="FOLIO"):
    """
    Fast syntax check without LLM calls
    Returns: (is_valid, errors)
    """
    errors = []

    if dataset_name == "FOLIO":
        # Check required sections
        if "Predicates:" not in logic_program:
            errors.append("Missing Predicates section")
        if "Premises:" not in logic_program:
            errors.append("Missing Premises section")
        if "Conclusion:" not in logic_program:
            errors.append("Missing Conclusion section")

        # Check parentheses balance
        if logic_program.count('(') != logic_program.count(')'):
            errors.append("Unbalanced parentheses")

        # Check for empty sections
        if "Predicates:\nPremises:" in logic_program:
            errors.append("Empty Predicates section")

    return len(errors) == 0, errors
