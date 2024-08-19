import os
import argparse
from nanotron.config import (
    AdamWOptimizerArgs,
    CheckpointsArgs,
    Config,
    DataArgs,
    DatasetStageArgs,
    GeneralArgs,
    LlamaConfig,
    LoggingArgs,
    LRSchedulerArgs,
    ModelArgs,
    OptimizerArgs,
    ParallelismArgs,
    PretrainDatasetsArgs,
    RandomInit,
    TokenizerArgs,
    TokensArgs,
)
from nanotron.logging import human_format

# Define model configuration for a tiny LLaMA model
model_config = LlamaConfig(
    bos_token_id=1,
    eos_token_id=2,
    hidden_act="silu",
    hidden_size=2048,
    initializer_range=0.02,
    intermediate_size=8192,
    max_position_embeddings=2048,
    num_attention_heads=32,
    num_hidden_layers=24,
    num_key_value_heads=32,
    pretraining_tp=1,
    rms_norm_eps=1e-05,
    rope_scaling=None,
    tie_word_embeddings=True,
    use_cache=True,
    vocab_size=50272,
)

# Calculate the number of parameters
num_params = human_format(
    model_config.vocab_size * model_config.hidden_size * 2
    + model_config.num_hidden_layers
    * (
        3 * model_config.hidden_size * model_config.intermediate_size
        + 4 * model_config.hidden_size * model_config.hidden_size
    )
).replace(".", "p")

print(f"Model has {num_params} parameters")

# Set seed for reproducibility
seed = 42

# Define learning rate scheduler arguments
learning_rate = LRSchedulerArgs(
    learning_rate=3e-4,
    lr_warmup_steps=500,
    lr_warmup_style="linear",
    lr_decay_style="cosine",
    min_decay_lr=3.0e-5,
)

# Define optimizer arguments
optimizer = OptimizerArgs(
    zero_stage=0,
    weight_decay=0.01,
    clip_grad=1.0,
    accumulate_grad_in_fp32=True,
    optimizer_factory=AdamWOptimizerArgs(
        adam_eps=1e-08,
        adam_beta1=0.9,
        adam_beta2=0.95,
        torch_adam_is_fused=True,
    ),
    learning_rate_scheduler=learning_rate,
)

# Define parallelism arguments
parallelism = ParallelismArgs(
    dp=1,
    pp=1,
    tp=1,
    pp_engine="1f1b",
    tp_mode="REDUCE_SCATTER",
    tp_linear_async_communication=True,
)

# Define token arguments
tokens = TokensArgs(sequence_length=2048, train_steps=10, micro_batch_size=2, batch_accumulation_per_replica=4)

# Set up checkpoint path
checkpoints_path = os.path.join(os.path.dirname(__file__), "checkpoints")
os.makedirs(checkpoints_path, exist_ok=True)

# Define the configuration object
config = Config(
    general=GeneralArgs(project="debug", run="tiny_llama_%date_%jobid", seed=seed),
    checkpoints=CheckpointsArgs(checkpoints_path=checkpoints_path, checkpoint_interval=10),
    parallelism=parallelism,
    model=ModelArgs(init_method=RandomInit(std=0.02), model_config=model_config),
    tokenizer=TokenizerArgs("gpt2"),
    optimizer=optimizer,
    logging=LoggingArgs(),
    tokens=tokens,
    profiler=None,
)

if __name__ == "__main__":
    # Argument parser for command-line arguments
    parser = argparse.ArgumentParser(description="Generate training config for Nanotron")
    parser.add_argument("--hf-url", type=str, required=True, help="The Hugging Face URL for the dataset")

    args = parser.parse_args()

    # Define data stages with the argument from the command line
    data_stages = [
        DatasetStageArgs(
            name="Stable Training Stage",
            start_training_step=1,
            data=DataArgs(
                dataset=PretrainDatasetsArgs(
                    hf_dataset_or_datasets=args.hf_url,
                    text_column_name="text",
                ),
                seed=seed,
            ),
        ),
        DatasetStageArgs(
            name="Annealing Phase",
            start_training_step=10,
            data=DataArgs(
                dataset=PretrainDatasetsArgs(
                    hf_dataset_or_datasets=args.hf_url,
                    text_column_name="text",
                ),
                seed=seed,
            ),
        ),
    ]

    # Update the config with the new data_stages
    config.data_stages = data_stages

    # Save the config as a YAML file
    config.save_as_yaml(os.path.join(os.path.dirname(__file__), "config.yaml"))

    print("Configuration file saved as config.yaml")
