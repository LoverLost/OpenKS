export EXP_NAME=FB13_temp_NSP_large_linearword_addlinearlayer_12_23_neg1_epoch10_bs8
export DATA_NAME=FB13_data
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
export EXP_ROOT=exp_root
export MODEL_CACHE_DIR=cache

python run_triplet_classification.py \
--do_train \
--do_predict \
--data_dir ./data/FB13 \
--per_device_train_batch_size 8 \
--per_device_eval_batch_size 8 \
--data_cache_dir ${EXP_ROOT}/cache_${DATA_NAME} \
--model_cache_dir ${MODEL_CACHE_DIR} \
--model_name_or_path bert-large-cased \
--model_type template \
--use_NSP \
--use_mlpencoder \
--word_embedding_type linear \
--top_additional_layer_type linear \
--top_layer_nums 12 23 \
--dropout_ratio 0.1 \
--begin_temp 10 \
--mid_temp 10 \
--end_temp 10 \
--num_neg 1 \
--only_corrupt_entity \
--margin 7 \
--max_seq_length 192 \
--learning_rate 1.5e-5 \
--adam_epsilon 1e-6 \
--num_train_epochs 10 \
--output_dir ${EXP_ROOT}/FB13_exps/out_${EXP_NAME} \
--gradient_accumulation_steps 1 \
--save_steps 2417 \
--warmup_steps 2417 \
--weight_decay 0.01 \
--text_loss_weight 0.0 \
--test_ratio 1.
