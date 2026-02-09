"""
Run Test-Driven Logic Inference
"""

import json
import os
from tqdm import tqdm
from symbolic_solvers.fol_solver.prover9_solver import FOL_Prover9_Program
from backup_answer_generation import Backup_Answer_Generator
from test_driven_logic import TestCaseGenerator, test_driven_inference_with_refinement

def main():
    # Configuration
    dataset_name = "FOLIO"
    split = "dev"
    model_name = "gpt-4"
    api_key = os.getenv('OPEN_API_KEY')

    print(f"\n{'='*70}")
    print(f"TEST-DRIVEN LOGIC INFERENCE")
    print(f"{'='*70}\n")

    # Load dataset
    input_file = f'./outputs/logic_programs/{dataset_name}_{split}_{model_name}.json'
    with open(input_file) as f:
        dataset = json.load(f)

    print(f"✓ Loaded {len(dataset)} examples")

    # Initialize
    test_generator = TestCaseGenerator(api_key, model_name="gpt-4", max_tokens=512)
    backup_generator = Backup_Answer_Generator(
        dataset_name, "LLM",
        f'./baselines/results/CoT_{dataset_name}_{split}_{model_name}.json'
    )
    program_executor = FOL_Prover9_Program

    print(f"✓ Initialized test generator and executor\n")

    # Statistics
    stats = {
        'total': len(dataset),
        'refined': 0,
        'refinement_improved': 0,
        'execution_success': 0,
        'parsing_errors': 0,
        'execution_errors': 0,
        'test_cases_generated': 0
    }

    outputs = []

    print(f"Processing examples...")
    print(f"{'='*70}\n")

    # Process subset first to test (faster iteration)
    # Comment out to run on full dataset
    # dataset = dataset[:50]  # Test on first 50

    for example in tqdm(dataset, desc="Test-driven inference"):
        # Run test-driven inference
        answer, flag, was_refined, refinement_history = test_driven_inference_with_refinement(
            example,
            program_executor,
            backup_generator,
            test_generator,
            max_refinement_attempts=2
        )

        # Update statistics
        if refinement_history['test_cases']:
            stats['test_cases_generated'] += 1

        if was_refined:
            stats['refined'] += 1
            # Check if refinement helped (comparing attempts)
            if refinement_history['refinements']:
                last_ref = refinement_history['refinements'][-1]
                if last_ref['confidence_after'] > last_ref['confidence_before']:
                    stats['refinement_improved'] += 1

        if flag == 'success':
            stats['execution_success'] += 1
        elif flag == 'parsing error':
            stats['parsing_errors'] += 1
        else:
            stats['execution_errors'] += 1

        # Create output
        output = {
            'id': example['id'],
            'context': example['context'],
            'question': example['question'],
            'answer': example['answer'],
            'predicted_answer': answer,
            'flag': flag,
            'was_refined': was_refined,
            'refinement_history': refinement_history
        }
        outputs.append(output)

    # Save results
    output_file = f'./outputs/logic_inference/{dataset_name}_{split}_{model_name}_test_driven.json'
    with open(output_file, 'w') as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)

    # Calculate accuracy
    correct = sum(1 for o in outputs if o['predicted_answer'] == o['answer'])
    accuracy = correct / len(outputs)

    # Print results
    print(f"\n{'='*70}")
    print(f"TEST-DRIVEN LOGIC INFERENCE RESULTS")
    print(f"{'='*70}")
    print(f"\n📊 Statistics:")
    print(f"  Total examples:              {stats['total']}")
    print(f"  Test cases generated:        {stats['test_cases_generated']} ({100*stats['test_cases_generated']/stats['total']:.1f}%)")
    print(f"  Programs refined:            {stats['refined']} ({100*stats['refined']/stats['total']:.1f}%)")
    print(f"  Refinements improved conf:   {stats['refinement_improved']} ({100*stats['refinement_improved']/max(1,stats['refined']):.1f}% of refined)")
    print(f"\n✅ Execution results:")
    print(f"  Successful:                  {stats['execution_success']} ({100*stats['execution_success']/stats['total']:.1f}%)")
    print(f"  Parsing errors:              {stats['parsing_errors']}")
    print(f"  Execution errors:            {stats['execution_errors']}")
    print(f"\n🎯 Final Accuracy: {accuracy:.4f} ({100*accuracy:.2f}%)")
    print(f"\n💾 Results saved to: {output_file}")
    print(f"{'='*70}\n")

    return accuracy, stats

if __name__ == '__main__':
    main()
