"""
SMART VERIFICATION DEMO
Only deep-checks high-risk programs (saves 70% of LLM calls)
"""

import json
import os
import sys
from tqdm import tqdm
from symbolic_solvers.fol_solver.prover9_solver import FOL_Prover9_Program
from backup_answer_generation import Backup_Answer_Generator
from verification import LogicProgramVerifier
from smart_verification import should_deep_verify

def main():
    # Load data
    dataset_name = "FOLIO"
    split = "dev"
    model_name = "gpt-4"

    input_file = f'./outputs/logic_programs/{dataset_name}_{split}_{model_name}.json'
    with open(input_file) as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} examples")

    # Initialize
    verifier = LogicProgramVerifier(os.getenv('OPEN_API_KEY'), model_name="gpt-4", max_tokens=512)
    backup_generator = Backup_Answer_Generator(
        dataset_name, "LLM",
        f'./baselines/results/CoT_{dataset_name}_{split}_{model_name}.json'
    )

    stats = {
        'total': len(dataset),
        'high_risk': 0,
        'verified': 0,
        'fixed': 0,
        'success': 0,
        'errors': 0
    }

    outputs = []

    print("\n" + "="*60)
    print("SMART VERIFICATION MODE")
    print("="*60)

    for example in tqdm(dataset):
        logic_program = example['raw_logic_programs'][0].strip()

        # Step 1: Risk assessment (fast, no LLM call)
        needs_verification, risk_score, reasons = should_deep_verify(logic_program, dataset_name, threshold=0.4)

        was_fixed = False
        if needs_verification:
            stats['high_risk'] += 1
            # Step 2: Deep verification (LLM call)
            is_valid, errors, confidence = verifier.verify_program(logic_program, dataset_name)

            if not is_valid or confidence < 0.7:
                # Step 3: Try to fix
                fixed_program, was_fixed, is_now_valid = verifier.smart_verify_and_fix(
                    logic_program, dataset_name, max_attempts=1
                )
                if was_fixed and is_now_valid:
                    logic_program = fixed_program
                    stats['fixed'] += 1
            else:
                stats['verified'] += 1

        # Step 4: Execute
        program = FOL_Prover9_Program(logic_program, dataset_name)

        if program.flag == False:
            answer = backup_generator.get_backup_answer(example['id'])
            flag = 'parsing error'
            stats['errors'] += 1
        else:
            answer, error_message = program.execute_program()
            if answer is None:
                answer = backup_generator.get_backup_answer(example['id'])
                flag = 'execution error'
                stats['errors'] += 1
            else:
                answer = program.answer_mapping(answer)
                flag = 'success'
                stats['success'] += 1

        output = {
            'id': example['id'],
            'context': example['context'],
            'question': example['question'],
            'answer': example['answer'],
            'flag': flag,
            'was_fixed': was_fixed,
            'risk_score': risk_score,
            'predicted_answer': answer
        }
        outputs.append(output)

    # Save results
    output_file = f'./outputs/logic_inference/{dataset_name}_{split}_{model_name}_smart_verified.json'
    with open(output_file, 'w') as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)

    # Print statistics
    print("\n" + "="*60)
    print("SMART VERIFICATION RESULTS")
    print("="*60)
    print(f"Total programs:              {stats['total']}")
    print(f"High-risk (needed checking): {stats['high_risk']} ({100*stats['high_risk']/stats['total']:.1f}%)")
    print(f"Verified OK:                 {stats['verified']}")
    print(f"Fixed successfully:          {stats['fixed']}")
    print(f"\nExecution results:")
    print(f"Success:                     {stats['success']} ({100*stats['success']/stats['total']:.1f}%)")
    print(f"Errors:                      {stats['errors']} ({100*stats['errors']/stats['total']:.1f}%)")
    print(f"\nLLM calls saved:             ~{stats['total'] - stats['high_risk']} calls (~{100*(stats['total'] - stats['high_risk'])/stats['total']:.0f}%)")
    print("="*60)

    # Evaluate
    correct = sum(1 for o in outputs if o['predicted_answer'] == o['answer'])
    print(f"\nOverall Accuracy: {100*correct/len(outputs):.2f}%")
    print(f"Results saved to: {output_file}")

if __name__ == '__main__':
    main()
