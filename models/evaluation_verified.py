"""Evaluation script for verified results"""
import json
import argparse

def full_evaluation(result_file):
    with open(result_file, 'r') as f:
        results = json.load(f)

    correct = 0
    executable = 0
    executable_correct = 0
    fixed_count = 0

    for example in results:
        pred = example['predicted_answer']
        gold = example['answer']

        # Check if was fixed
        if example.get('was_fixed', False):
            fixed_count += 1

        # Check if executable
        if example['flag'] == 'success':
            executable += 1
            if pred == gold:
                executable_correct += 1

        # Overall accuracy
        if pred == gold:
            correct += 1

    total = len(results)
    print(f"Overall accuracy: {correct/total}")
    print(f"Executable rate (Exe_Rate): {executable/total}")
    if executable > 0:
        print(f"Executable accuracy (Exe_Acc): {executable_correct/executable}")
    print(f"Programs fixed by verification: {fixed_count}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_name', type=str, required=True)
    parser.add_argument('--model_name', type=str, required=True)
    parser.add_argument('--split', type=str, required=True)
    args = parser.parse_args()

    result_file = f'./outputs/logic_inference/{args.dataset_name}_{args.split}_{args.model_name}_verified.json'
    full_evaluation(result_file)
