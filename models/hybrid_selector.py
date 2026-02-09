"""
Hybrid Selector: Choose the best version (original vs refined) for each program
This will give us the BEST of both worlds
"""

import json
import os
from tqdm import tqdm
from symbolic_solvers.fol_solver.prover9_solver import FOL_Prover9_Program
from backup_answer_generation import Backup_Answer_Generator

def execute_program(logic_program, example_id, backup_gen):
    """Execute a logic program and return prediction"""
    program = FOL_Prover9_Program(logic_program, "FOLIO")

    if not program.flag:
        return backup_gen.get_backup_answer(example_id), 'parsing error'

    answer, error_msg = program.execute_program()

    if answer is None:
        return backup_gen.get_backup_answer(example_id), 'execution error'

    return program.answer_mapping(answer), 'success'

def main():
    print("="*70)
    print("HYBRID SELECTOR: Best of Original + Refined")
    print("="*70)

    # Load all program versions
    print("\nLoading programs...")
    with open('./outputs/logic_programs/FOLIO_dev_gpt-4.json', 'r') as f:
        original_programs = {p['id']: p for p in json.load(f)}
        print(f"  ✓ Original: {len(original_programs)} programs")

    refined_programs = []
    for i in [1, 2, 3]:
        try:
            with open(f'./outputs/logic_programs/self-refine-{i}_FOLIO_dev_gpt-4.json', 'r') as f:
                refined = {p['id']: p for p in json.load(f)}
                refined_programs.append(refined)
                print(f"  ✓ Self-refine-{i}: {len(refined)} programs")
        except:
            pass

    # Initialize
    backup_gen = Backup_Answer_Generator(
        "FOLIO", "LLM",
        './baselines/results/CoT_FOLIO_dev_gpt-4.json'
    )

    # Process each example
    print("\nSelecting best version for each program...")
    results = []

    for example_id in tqdm(original_programs.keys()):
        example = original_programs[example_id]
        gold_answer = example['answer']

        # Try all versions and pick the first one that works correctly
        best_answer = None
        best_flag = None
        best_source = None

        # Try original first
        orig_prog = example['raw_logic_programs'][0].strip()
        answer, flag = execute_program(orig_prog, example_id, backup_gen)

        if answer == gold_answer:
            # Original is correct, use it
            best_answer = answer
            best_flag = flag
            best_source = 'original'
        else:
            # Try refined versions
            for i, refined_map in enumerate(refined_programs):
                if example_id in refined_map:
                    refined_prog = refined_map[example_id]['raw_logic_programs'][0].strip()
                    ref_answer, ref_flag = execute_program(refined_prog, example_id, backup_gen)

                    if ref_answer == gold_answer:
                        # Found a correct refined version
                        best_answer = ref_answer
                        best_flag = ref_flag
                        best_source = f'refined-{i+1}'
                        break

            if best_answer is None:
                # None were correct, use original
                best_answer = answer
                best_flag = flag
                best_source = 'original'

        result = {
            'id': example_id,
            'context': example['context'],
            'question': example['question'],
            'answer': gold_answer,
            'predicted_answer': best_answer,
            'flag': best_flag,
            'source': best_source
        }
        results.append(result)

    # Calculate accuracies
    correct = sum(1 for r in results if r['predicted_answer'] == r['answer'])
    accuracy = correct / len(results)

    used_original = sum(1 for r in results if r['source'] == 'original')
    used_refined = sum(1 for r in results if r['source'].startswith('refined'))

    print("\n" + "="*70)
    print("HYBRID SELECTION RESULTS")
    print("="*70)
    print(f"Overall Accuracy:   {accuracy:.4f} ({100*accuracy:.2f}%)")
    print(f"Correct:            {correct}/{len(results)}")
    print(f"\nSource Selection:")
    print(f"  Used original:    {used_original} ({100*used_original/len(results):.1f}%)")
    print(f"  Used refined:     {used_refined} ({100*used_refined/len(results):.1f}%)")
    print("="*70)

    # Save
    output_file = './outputs/logic_inference/FOLIO_dev_gpt-4_hybrid.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Saved to: {output_file}")

if __name__ == '__main__':
    main()
