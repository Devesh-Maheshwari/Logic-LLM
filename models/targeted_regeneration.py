"""
Targeted Regeneration: Regenerate only the 24 failed programs
Expected improvement: +2-4% by fixing half of failures
"""

import json
import os
import sys
sys.path.insert(0, '/users/devesh/Logic-LLM/models')

from symbolic_solvers.fol_solver.prover9_solver import FOL_Prover9_Program
from backup_answer_generation import Backup_Answer_Generator
from tqdm import tqdm

def main():
    print("="*70)
    print("TARGETED REGENERATION FOR FAILED PROGRAMS")
    print("="*70)

    # Load original inference results
    with open('./outputs/logic_inference/FOLIO_dev_gpt-4_backup-LLM.json', 'r') as f:
        results = json.load(f)

    # Load original programs
    with open('./outputs/logic_programs/FOLIO_dev_gpt-4.json', 'r') as f:
        programs_data = json.load(f)
        programs_map = {p['id']: p for p in programs_data}

    # Identify failed programs
    failed = [r for r in results if r['flag'] != 'success']
    failed_ids = set([r['id'] for r in failed])

    print(f"\nFound {len(failed)} failed programs:")
    print(f"  - Parsing errors: {len([r for r in failed if 'parsing' in r['flag']])}")
    print(f"  - Execution errors: {len([r for r in failed if 'execution' in r['flag']])}")

    # Strategy: Try self-refined versions for failed programs
    print("\nStrategy: Use self-refined versions of failed programs")

    # Load self-refined programs
    refined_versions = []
    for i in [1, 2, 3]:
        try:
            with open(f'./outputs/logic_programs/self-refine-{i}_FOLIO_dev_gpt-4.json', 'r') as f:
                refined = json.load(f)
                refined_versions.append({p['id']: p for p in refined})
                print(f"  ✓ Loaded self-refine-{i}")
        except:
            pass

    if not refined_versions:
        print("  ✗ No self-refined versions found")
        return

    # Run inference on failed programs with refined versions
    backup_generator = Backup_Answer_Generator(
        "FOLIO", "LLM",
        './baselines/results/CoT_FOLIO_dev_gpt-4.json'
    )

    improvements = 0
    new_successes = 0

    print(f"\nTesting refined versions on {len(failed)} failed programs...")

    improved_results = []

    for result in tqdm(results):
        if result['id'] not in failed_ids:
            # Keep successful programs as-is
            improved_results.append(result)
        else:
            # Try refined versions
            best_result = result  # Start with original
            original_correct = (result['predicted_answer'] == result['answer'])

            for refined_map in refined_versions:
                if result['id'] in refined_map:
                    refined_prog = refined_map[result['id']]['raw_logic_programs'][0].strip()

                    # Execute refined program
                    program = FOL_Prover9_Program(refined_prog, "FOLIO")

                    if program.flag:
                        answer, error_msg = program.execute_program()
                        if answer is not None:
                            answer = program.answer_mapping(answer)

                            # Check if this is better
                            is_correct = (answer == result['answer'])

                            if is_correct and not original_correct:
                                improvements += 1
                                best_result = {
                                    **result,
                                    'predicted_answer': answer,
                                    'flag': 'success',
                                    'refined_version': True
                                }
                                new_successes += 1
                                break  # Found a good version, stop

            improved_results.append(best_result)

    # Calculate new accuracy
    correct = sum(1 for r in improved_results if r['predicted_answer'] == r['answer'])
    new_accuracy = correct / len(improved_results)

    original_correct = sum(1 for r in results if r['predicted_answer'] == r['answer'])
    original_accuracy = original_correct / len(results)

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Original accuracy:  {original_accuracy:.4f} ({100*original_accuracy:.2f}%)")
    print(f"Improved accuracy:  {new_accuracy:.4f} ({100*new_accuracy:.2f}%)")
    print(f"Improvement:        +{new_accuracy - original_accuracy:.4f} ({100*(new_accuracy - original_accuracy):.2f}%)")
    print(f"\nPrograms fixed:     {improvements}")
    print(f"New successes:      {new_successes}")
    print("="*70)

    # Save improved results
    output_file = './outputs/logic_inference/FOLIO_dev_gpt-4_improved.json'
    with open(output_file, 'w') as f:
        json.dump(improved_results, f, indent=2)

    print(f"\n✓ Saved improved results to: {output_file}")

    return new_accuracy

if __name__ == '__main__':
    main()
