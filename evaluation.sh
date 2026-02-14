# 1. Navigate and activate environment
cd /users/devesh/Logic-LLM
source venv/bin/activate
source .env

# For GPT-3.5-turbo
python models/logic_program.py \
    --api_key "${OPEN_API_KEY}" \
    --dataset_name "FOLIO" \
    --split dev \
    --model_name "gpt-3.5-turbo" \
    --max_new_tokens 1024

# For GPT-4 (recommended for best results)
python models/logic_program.py \
    --api_key "${OPEN_API_KEY}" \
    --dataset_name "FOLIO" \
    --split dev \
    --model_name "gpt-4" \
    --max_new_tokens 1024


# 2. Run Logic Inference (executes logic programs with symbolic solver):
# For GPT-3.5-turbo
python models/logic_inference.py \
    --model_name "gpt-3.5-turbo" \
    --dataset_name "FOLIO" \
    --split dev \
    --backup_strategy LLM \
    --backup_LLM_result_path ./baselines/results/CoT_FOLIO_dev_gpt-3.5-turbo.json

# For GPT-4
python models/logic_inference.py \
    --model_name "gpt-4" \
    --dataset_name "FOLIO" \
    --split dev \
    --backup_strategy LLM \
    --backup_LLM_result_path ./baselines/results/CoT_FOLIO_dev_gpt-4.json

# 3. Evaluate Logic-LLM Results:

# For GPT-3.5-turbo
python models/evaluation.py \
    --dataset_name "FOLIO" \
    --model_name "gpt-3.5-turbo" \
    --split dev \
    --backup LLM

# For GPT-4
python models/evaluation.py \
    --dataset_name "FOLIO" \
    --model_name "gpt-4" \
    --split dev \
    --backup LLM

DATASET="FOLIO"
SPLIT="dev"
MODEL="gpt-4"
BACKUP="LLM"
python models/logic_inference.py \
    --model_name ${MODEL} \
    --dataset_name ${DATASET} \
    --split ${SPLIT} \
    --backup_strategy ${BACKUP} \
    --backup_LLM_result_path ./baselines/results/CoT_${DATASET}_${SPLIT}_${MODEL}.json

python models/self_refinement.py \
    --model_name "gpt-4" \
    --dataset_name "FOLIO" \
    --split dev \
    --backup_strategy "LLM" \
    --backup_LLM_result_path ./baselines/results/CoT_FOLIO_dev_gpt-4.json \
    --api_key "${OPEN_API_KEY}" \
    --maximum_rounds 3

# 4. Evaluate baseline results (need to be in baselines directory)
cd baselines
python evaluation.py --dataset_name "FOLIO" --model_name "gpt-3.5-turbo" --split "dev" --mode "Direct" | grep "EM:"
python evaluation.py --dataset_name "FOLIO" --model_name "gpt-3.5-turbo" --split "dev" --mode "CoT" | grep "EM:"
python evaluation.py --dataset_name "FOLIO" --model_name "gpt-4" --split "dev" --mode "Direct" | grep "EM:"
python evaluation.py --dataset_name "FOLIO" --model_name "gpt-4" --split "dev" --mode "CoT" | grep "EM:"


