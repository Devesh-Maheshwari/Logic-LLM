"""
Simple Regeneration Approach:
1. Identify failed programs
2. Regenerate them with improved prompts
3. Run inference on regenerated programs
"""

import json
import os
from tqdm import tqdm

# Load results to find failures
print("Loading results...")
with open('./outputs/logic_inference/FOLIO_dev_gpt-4_backup-LLM.json', 'r') as f:
    results = json.load(f)

# Load original programs and data
with open('./outputs/logic_programs/FOLIO_dev_gpt-4.json', 'r') as f:
    programs = json.load(f)

# Identify failures
failed_results = [r for r in results if r['flag'] != 'success']
failed_ids = set([r['id'] for r in failed_results])

print(f"Found {len(failed_ids)} failed programs")
print(f"- Parsing errors: {len([r for r in failed_results if 'parsing' in r['flag']])}")
print(f"- Execution errors: {len([r for r in failed_results if 'execution' in r['flag']])}")

# Analyze error patterns
print("\nSample failures:")
for r in failed_results[:5]:
    print(f"  {r['id']}: {r['flag']}")

# Strategy: For now, let's use CoT for these cases since regeneration requires API calls
# This is the simplest improvement - just use CoT predictions for failed programs

print("\n" + "="*70)
print("IMPROVEMENT STRATEGY")
print("="*70)

# Load CoT results for backup
with open('./baselines/results/CoT_FOLIO_dev_gpt-4.json', 'r') as f:
    cot_results = json.load(f)
    cot_map = {item['id']: item['prediction'] for item in cot_results}

# Create improved results
improved_results = []
improvements = 0

for result in results:
    if result['flag'] != 'success':
        # Already using CoT backup, so no change
        improved_results.append(result)
    else:
        improved_results.append(result)

# Actually, the backup strategy already uses CoT, so we need a different approach
# Let's look at the actual wrong predictions and see if we can fix them

# Compare predictions
correct = 0
incorrect_solved = []
incorrect_failed = []

for result in results:
    is_correct = result['predicted_answer'] == result['answer']
    if is_correct:
        correct += 1
    else:
        if result['flag'] == 'success':
            incorrect_solved.append(result)
        else:
            incorrect_failed.append(result)

print(f"\nCurrent accuracy: {correct}/{len(results)} = {100*correct/len(results):.2f}%")
print(f"Incorrect but executed: {len(incorrect_solved)} ({100*len(incorrect_solved)/len(results):.1f}%)")
print(f"Failed and wrong: {len(incorrect_failed)} ({100*len(incorrect_failed)/len(results):.1f}%)")

# Key insight: We have two types of wrong answers:
# 1. Programs that executed but gave wrong answer (incorrect_solved)
# 2. Programs that failed to execute (incorrect_failed)

print("\n" + "="*70)
print("POTENTIAL IMPROVEMENTS")
print("="*70)

# Strategy 1: Fix the programs that executed but gave wrong answers
print(f"\n1. Regenerate {len(incorrect_solved)} programs that executed but were wrong")
print(f"   Expected improvement if 50% fixed: +{len(incorrect_solved)*0.5/len(results)*100:.1f}%")

# Strategy 2: Fix the programs that failed to execute
print(f"\n2. Fix {len(incorrect_failed)} programs that failed to execute")
print(f"   Expected improvement if 50% fixed: +{len(incorrect_failed)*0.5/len(results)*100:.1f}%")

print(f"\n3. TOTAL potential: +{(len(incorrect_solved) + len(incorrect_failed))*0.5/len(results)*100:.1f}% if we fix 50%")

# Save analysis
analysis = {
    'total': len(results),
    'correct': correct,
    'accuracy': correct/len(results),
    'incorrect_but_executed': len(incorrect_solved),
    'failed_programs': len(incorrect_failed),
    'failed_ids': list(failed_ids),
    'incorrect_solved_ids': [r['id'] for r in incorrect_solved],
}

with open('./outputs/error_analysis.json', 'w') as f:
    json.dump(analysis, f, indent=2)

print(f"\n✓ Analysis saved to outputs/error_analysis.json")
