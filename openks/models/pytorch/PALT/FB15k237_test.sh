export DATA_NAME=FB15k237_data
export MODEL_CACHE_DIR=cache

python run_link_prediction.py \
--do_predict \
--data_dir ./data/FB15k-237 \
--per_device_eval_batch_size 512 \
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
--begin_temp 2 \
--mid_temp 0 \
--end_temp 0 \
--num_neg 1 \
--only_corrupt_entity \
--margin 7 \
--max_seq_length 192 \
--learning_rate 5e-5 \
--adam_epsilon 1e-6 \
--num_train_epochs 10 \
--output_dir ${EXP_ROOT}/THIS_SHOULD_BE_EMPTY \
--gradient_accumulation_steps 1 \
--save_steps 4252 \
--warmup_steps 4252 \
--weight_decay 0.01 \
--text_loss_weight 0.0 \
--test_ratio 1. \
--load_checkpoint \
--checkpoint_dir ${EXP_ROOT}/FB15K237_exps/out_FB15k237_large_wordlinear_toplinear_12_23_epoch10_bs8_lr_1e_4 \
--not_print_model \
--test_count 24 \
--test_worker_id ${WORKER_ID} \
