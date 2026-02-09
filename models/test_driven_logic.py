"""
Test-Driven Logic Generation
Generate test cases from problem, validate programs against them
"""

import json
import re
from utils import OpenAIModel

class TestCaseGenerator:
    def __init__(self, api_key, model_name="gpt-4", max_tokens=512):
        self.llm = OpenAIModel(api_key, model_name, stop_words=[], max_new_tokens=max_tokens)

    def generate_test_cases(self, context, question, dataset_name="FOLIO"):
        """
        Generate test cases from problem statement
        Returns: list of test constraints
        """
        if dataset_name == "FOLIO":
            return self._generate_folio_tests(context, question)
        return []

    def _generate_folio_tests(self, context, question):
        """Generate test cases for FOLIO logical reasoning"""

        prompt = f"""Given this logical reasoning problem, extract 3-5 KEY LOGICAL CONSTRAINTS that any correct formalization must satisfy.

CONTEXT:
{context}

QUESTION:
{question}

INSTRUCTIONS:
1. Identify the most important logical relationships mentioned
2. For each relationship, write a constraint that a correct logic program MUST satisfy
3. Focus on: implications, mutual exclusivity, necessary conditions
4. Be specific about predicate names and logical operators

FORMAT (output ONLY the constraints, one per line):
- [constraint description]
- [constraint description]
...

EXAMPLE OUTPUT:
- If Perform(x) is true, then Attend(x) must be true (from "If people perform in school talent shows often, then they attend")
- Perform(x) and Inactive(x) cannot both be true (from "either perform OR inactive")
- If Chaperone(x) is true, then Student(x) must be false (from "If people chaperone, then they are not students")

OUTPUT (3-5 constraints for the given problem):
"""

        try:
            response = self.llm.generate(prompt).strip()
            constraints = [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
            return constraints[:5]  # Max 5 constraints
        except:
            return []

    def validate_program_with_constraints(self, logic_program, constraints, dataset_name="FOLIO"):
        """
        Check if logic program satisfies the given constraints
        Returns: (is_valid, violations, confidence)
        """
        if not constraints:
            return True, [], 1.0

        prompt = f"""You are validating a logic program against key constraints.

LOGIC PROGRAM:
{logic_program}

CONSTRAINTS TO CHECK:
{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(constraints))}

TASK:
For each constraint, check if the logic program correctly captures it.

OUTPUT FORMAT:
Constraint 1: [PASS/FAIL] - [brief reason]
Constraint 2: [PASS/FAIL] - [brief reason]
...

Overall: [PASS/FAIL]

VALIDATION:
"""

        try:
            response = self.llm.generate(prompt).strip()

            # Parse response
            violations = []
            for line in response.split('\n'):
                if 'FAIL' in line.upper():
                    violations.append(line.strip())

            # Overall assessment
            is_valid = 'Overall: PASS' in response or len(violations) == 0

            confidence = max(0.0, 1.0 - (len(violations) / max(len(constraints), 1)))

            return is_valid, violations, confidence
        except:
            return True, [], 0.5  # If validation fails, assume OK but low confidence

    def fix_with_constraints(self, logic_program, constraints, violations, dataset_name="FOLIO"):
        """
        Fix logic program based on constraint violations
        Returns: (fixed_program, success)
        """
        if not violations:
            return logic_program, False

        prompt = f"""Fix the logic program to satisfy the failed constraints.

ORIGINAL LOGIC PROGRAM:
{logic_program}

FAILED CONSTRAINTS:
{chr(10).join(violations)}

ORIGINAL CONSTRAINTS (for reference):
{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(constraints))}

INSTRUCTIONS:
1. Identify what's wrong with the original formalization
2. Fix ONLY the parts that violate constraints
3. Keep the overall structure and format
4. Ensure all constraints are satisfied

OUTPUT THE CORRECTED LOGIC PROGRAM ONLY (no explanations):
"""

        try:
            fixed_program = self.llm.generate(prompt).strip()
            return fixed_program, True
        except:
            return logic_program, False


def test_driven_inference_with_refinement(
    example,
    program_executor,
    backup_generator,
    test_generator,
    max_refinement_attempts=2
):
    """
    Execute logic program with test-driven validation and refinement

    Returns: (answer, flag, was_refined, refinement_history)
    """
    context = example['context']
    question = example['question']
    logic_program = example['raw_logic_programs'][0].strip()
    dataset_name = "FOLIO"  # Assuming FOLIO for now

    refinement_history = {
        'original_program': logic_program,
        'attempts': 0,
        'test_cases': [],
        'refinements': []
    }

    # Step 1: Generate test cases
    test_cases = test_generator.generate_test_cases(context, question, dataset_name)
    refinement_history['test_cases'] = test_cases

    if not test_cases:
        # No tests generated, proceed with original program
        answer, flag, error_msg = execute_program(logic_program, example['id'], program_executor, backup_generator, dataset_name)
        return answer, flag, False, refinement_history

    # Step 2: Validate program against test cases
    is_valid, violations, confidence = test_generator.validate_program_with_constraints(
        logic_program, test_cases, dataset_name
    )

    current_program = logic_program
    was_refined = False

    # Step 3: Refinement loop if needed
    if not is_valid or confidence < 0.7:
        for attempt in range(max_refinement_attempts):
            refinement_history['attempts'] += 1

            # Try to fix
            fixed_program, fix_success = test_generator.fix_with_constraints(
                current_program, test_cases, violations, dataset_name
            )

            if not fix_success:
                break

            # Validate the fix
            is_fixed_valid, new_violations, new_confidence = test_generator.validate_program_with_constraints(
                fixed_program, test_cases, dataset_name
            )

            refinement_info = {
                'attempt': attempt + 1,
                'violations_before': len(violations),
                'violations_after': len(new_violations),
                'confidence_before': confidence,
                'confidence_after': new_confidence
            }
            refinement_history['refinements'].append(refinement_info)

            # If improved, use the fixed version
            if new_confidence > confidence or len(new_violations) < len(violations):
                current_program = fixed_program
                was_refined = True
                violations = new_violations
                confidence = new_confidence

                # If now valid, stop refining
                if is_fixed_valid and new_confidence >= 0.8:
                    break
            else:
                # Fix didn't help, stop
                break

    # Step 4: Execute the (possibly refined) program
    answer, flag, error_msg = execute_program(
        current_program, example['id'], program_executor, backup_generator, dataset_name
    )

    return answer, flag, was_refined, refinement_history


def execute_program(logic_program, example_id, program_executor, backup_generator, dataset_name):
    """Execute logic program and return result"""
    program = program_executor(logic_program, dataset_name)

    if program.flag == False:
        answer = backup_generator.get_backup_answer(example_id)
        return answer, 'parsing error', ''

    answer, error_message = program.execute_program()

    if answer is None:
        answer = backup_generator.get_backup_answer(example_id)
        return answer, 'execution error', error_message

    answer = program.answer_mapping(answer)
    return answer, 'success', ''
