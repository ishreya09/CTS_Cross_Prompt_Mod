#!/usr/bin/env bash
model_name='attribute_attention'
seed=32
prompt=1

python train_CTS.py --test_prompt_id ${prompt} --model_name ${model_name} --seed ${seed}