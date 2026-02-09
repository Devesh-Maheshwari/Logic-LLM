"""
Enhanced Logic Inference with Pre-Execution Verification
"""

import json
import os
from tqdm import tqdm
from symbolic_solvers.fol_solver.prover9_solver import FOL_Prover9_Program
try:
    from symbolic_solvers.pyke_solver.pyke_solver import Pyke_Program
except ImportError:
    Pyke_Program = None  # Not available in Python 3.12+
from symbolic_solvers.csp_solver.csp_solver import CSP_Program
from symbolic_solvers.z3_solver.sat_problem_solver import LSAT_Z3_Program
import argparse
import random
from backup_answer_generation import Backup_Answer_Generator
from verification import LogicProgramVerifier, quick_syntax_check

class VerifiedLogicInferenceEngine:
    def __init__(self, args):
        self.args = args
        self.dataset_name = args.dataset_name
        self.split = args.split
        self.model_name = args.model_name
        self.save_path = args.save_path
        self.backup_strategy = args.backup_strategy
        self.use_verification = args.use_verification

        # Initialize verifier if enabled
        self.verifier = None
        if self.use_verification and hasattr(args, 'api_key') and args.api_key:
            try:
                self.verifier = LogicProgramVerifier(args.api_key, model_name="gpt-4", max_tokens=512)
                print(f"✓ Verification enabled with GPT-4")
            except:
                print(f"✗ Could not initialize verifier, running without verification")
                self.use_verification = False

        self.dataset = self.load_logic_programs()
        program_executor_map = {'FOLIO': FOL_Prover9_Program,
                                'ProntoQA': Pyke_Program,
                                'ProofWriter': Pyke_Program,
                                'LogicalDeduction': CSP_Program,
                                'AR-LSAT': LSAT_Z3_Program}
        self.program_executor = program_executor_map[self.dataset_name]
        self.backup_generator = Backup_Answer_Generator(self.dataset_name, self.backup_strategy, self.args.backup_LLM_result_path)

        # Statistics
        self.stats = {
            'total': 0,
            'verified_ok': 0,
            'fixed': 0,
            'fix_failed': 0,
            'execution_success': 0,
            'execution_error': 0,
            'parsing_error': 0
        }

    def load_logic_programs(self):
        with open(os.path.join('./outputs/logic_programs', f'{self.dataset_name}_{self.split}_{self.model_name}.json')) as f:
            dataset = json.load(f)
        print(f"Loaded {len(dataset)} examples from {self.split} split.")
        return dataset

    def save_results(self, outputs):
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

        suffix = 'verified' if self.use_verification else f'backup-{self.backup_strategy}'
        filename = f'{self.dataset_name}_{self.split}_{self.model_name}_{suffix}.json'

        with open(os.path.join(self.save_path, filename), 'w') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {filename}")
        self._print_statistics()

    def _print_statistics(self):
        """Print verification statistics"""
        if not self.use_verification:
            return

        print("\n" + "="*60)
        print("VERIFICATION STATISTICS")
        print("="*60)
        print(f"Total programs:           {self.stats['total']}")
        print(f"Verified OK (no fix):     {self.stats['verified_ok']} ({100*self.stats['verified_ok']/max(1, self.stats['total']):.1f}%)")
        print(f"Fixed successfully:       {self.stats['fixed']} ({100*self.stats['fixed']/max(1, self.stats['total']):.1f}%)")
        print(f"Fix failed:               {self.stats['fix_failed']} ({100*self.stats['fix_failed']/max(1, self.stats['total']):.1f}%)")
        print(f"\nExecution success:        {self.stats['execution_success']} ({100*self.stats['execution_success']/max(1, self.stats['total']):.1f}%)")
        print(f"Parsing errors:           {self.stats['parsing_error']}")
        print(f"Execution errors:         {self.stats['execution_error']}")
        print("="*60)

    def safe_execute_program(self, id, logic_program, verify=True):
        """Execute with optional pre-execution verification"""

        self.stats['total'] += 1
        original_program = logic_program
        was_fixed = False

        # Pre-execution verification
        if verify and self.use_verification and self.verifier:
            # ALWAYS do deep verification with LLM (not just quick check)
            is_valid, errors, confidence = self.verifier.verify_program(
                logic_program, self.dataset_name
            )

            if not is_valid or confidence < 0.8:
                # Try to fix with verifier
                fixed_program, was_fixed, is_now_valid = self.verifier.smart_verify_and_fix(
                    logic_program, self.dataset_name, max_attempts=1
                )

                if was_fixed:
                    if is_now_valid:
                        logic_program = fixed_program
                        self.stats['fixed'] += 1
                    else:
                        self.stats['fix_failed'] += 1
                        # Use fixed version anyway, might be better
                        logic_program = fixed_program
            else:
                self.stats['verified_ok'] += 1

        # Execute the program (original or fixed)
        program = self.program_executor(logic_program, self.dataset_name)

        # cannot parse the program
        if program.flag == False:
            self.stats['parsing_error'] += 1
            answer = self.backup_generator.get_backup_answer(id)
            return answer, 'parsing error', '', was_fixed

        # execute the program
        answer, error_message = program.execute_program()

        # not executable
        if answer is None:
            self.stats['execution_error'] += 1
            answer = self.backup_generator.get_backup_answer(id)
            return answer, 'execution error', error_message, was_fixed

        # successfully executed
        self.stats['execution_success'] += 1
        answer = program.answer_mapping(answer)
        return answer, 'success', '', was_fixed

    def inference_on_dataset(self):
        outputs = []
        error_count = 0

        for example in tqdm(self.dataset):
            # execute the logic program with verification
            answer, flag, error_message, was_fixed = self.safe_execute_program(
                example['id'],
                example['raw_logic_programs'][0].strip(),
                verify=True
            )

            if not flag == 'success':
                error_count += 1

            # create output
            output = {'id': example['id'],
                    'context': example['context'],
                    'question': example['question'],
                    'answer': example['answer'],
                    'flag': flag,
                    'was_fixed': was_fixed,
                    'predicted_answer': answer}
            outputs.append(output)

        print(f"Error count: {error_count}")
        return outputs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_name', type=str, default='FOLIO')
    parser.add_argument('--split', type=str, default='dev')
    parser.add_argument('--save_path', type=str, default='./outputs/logic_inference')
    parser.add_argument('--backup_strategy', type=str, default='random', choices=['random', 'LLM'])
    parser.add_argument('--backup_LLM_result_path', type=str, default=None)
    parser.add_argument('--model_name', type=str, default='gpt-4')
    parser.add_argument('--timeout', type=int, default=10)
    parser.add_argument('--use_verification', type=bool, default=True, help='Enable pre-execution verification')
    parser.add_argument('--api_key', type=str, default=None, help='OpenAI API key for verification')

    args = parser.parse_args()

    engine = VerifiedLogicInferenceEngine(args)
    outputs = engine.inference_on_dataset()
    engine.save_results(outputs)

if __name__ == '__main__':
    main()
