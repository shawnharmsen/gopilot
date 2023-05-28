import argparse
import dataclasses
import logging
import random
from typing import Union

import numpy as np
import torch

import flame
from dataset import GopilotFineTuningDataset
from model.model import GopilotModel
from tokenizer import GopilotTokenizer, HuggingFaceTokenizer


@dataclasses.dataclass
class Args:
    model: str
    model_cf: str
    tokenizer: str
    tokenizer_cf: str
    checkpoint_filepath: str
    output_filepath: str
    dataset_filepath: str

@dataclasses.dataclass
class TrainingParametersArgs:
    gradient_accumulation_steps: int
    batch_size: int
    dropout: float
    weight_decay: float
    lr: float
    epsilon: float
    num_epochs: int
    clip_gradients: float
    precision: Union[str, torch.dtype]
    seed: int

@dataclasses.dataclass
class S3Args:
    s3_bucket: str
    s3_cache_dir: str
    s3_checkpoints: bool

@dataclasses.dataclass
class RunArgs:
    device: Union[str, torch.device]
    verbose: bool
    neptune: bool
    compile: bool
    checkpoints_dir: str


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    # General arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-cf', type=str, required=True, help='Path to the model configuration file.')
    parser.add_argument('--tokenizer-cf', type=str, required=True, help='Path to the tokenizer configuration file.')
    parser.add_argument('--model', type=str, default="Gopilot", help='Name of the model to use.', choices=["gopilot"])
    parser.add_argument('--tokenizer', type=str, default="Gopilot", help='Name of the tokenizer to use.', choices=["gopilot", "hugging-face"])
    parser.add_argument('--checkpoint-filepath', type=str, default=None, help='Path to the checkpoint file.')
    parser.add_argument('--output-filepath', type=str, default=None, help='Path to the output file.')
    parser.add_argument('--dataset-filepath', type=str, default=None, help='Path to the JSONL dataset file.')
    args, remaining_args = parser.parse_known_args()
    # Training parameters
    tp_parser = argparse.ArgumentParser()
    tp_parser.add_argument('--gradient-accumulation-steps', type=int, default=1, help='Number of gradient accumulation steps.')
    tp_parser.add_argument('--batch-size', type=int, default=1, help='Batch size.')
    tp_parser.add_argument('--dropout', type=float, default=0.1, help='Dropout probability.')
    tp_parser.add_argument('--weight-decay', type=float, default=0.1, help='Weight decay value.')
    tp_parser.add_argument('--lr', type=float, default=1e-5, help='Learning rate.')
    tp_parser.add_argument('--epsilon', type=float, default=1e-8, help='Epsilon value for AdamW.')
    tp_parser.add_argument('--num-epochs', type=int, default=1, help='Number of epochs.')
    tp_parser.add_argument('--clip-gradients', type=float, default=1.0, help='Clip gradients.')
    tp_parser.add_argument('--precision', type=str, default="float32", help='Precision.')
    tp_parser.add_argument('--seed', type=int, default=42, help='Random seed.')
    tp_args, remaining_args = tp_parser.parse_known_args(remaining_args)
    # S3 arguments
    s3_parser = argparse.ArgumentParser()
    s3_parser.add_argument('--s3-bucket', type=str, default=None, help='S3 bucket.')
    s3_parser.add_argument('--s3-cache-dir', type=str, default=None, help='S3 cache directory.')
    s3_parser.add_argument('--s3-checkpoints', action='store_true', help='Upload checkpoints to S3.')
    s3_args, remaining_args = s3_parser.parse_known_args(remaining_args)
    # Run arguments
    run_parser = argparse.ArgumentParser()
    run_parser.add_argument('--device', type=str, default="cuda", help='Device to use.', choices=["cpu", "cuda"])
    run_parser.add_argument('--verbose', action='store_true', help='Verbose.')
    run_parser.add_argument('--neptune', action='store_true', help='Log to Neptune.')
    run_parser.add_argument('--compile', action='store_true', help='Compile model.')
    run_parser.add_argument('--checkpoints-dir', type=str, default=None, help='Checkpoints directory.')
    run_args = run_parser.parse_args(remaining_args)

    # Parse args
    args = Args(**vars(args))
    tp_args = TrainingParametersArgs(**vars(tp_args))
    s3_args = S3Args(**vars(s3_args))
    run_args = RunArgs(**vars(run_args))

    # Check S3
    assert flame.s3_is_available(), "S3 is not available. Please set the relevant environment variables."

    # Seed for reproducibility
    torch.manual_seed(tp_args.seed)
    np.random.seed(tp_args.seed)
    random.seed(tp_args.seed)

    # Transform args
    run_args.device = flame.best_device() if run_args.device == "auto" else torch.device(run_args.device)
    tp_args.precision = torch.float32 if tp_args.precision == "fp32" else torch.float16

    # Model
    model = GopilotModel.from_config_file(args.model_cf, tp_args.dropout)
    
    # Load model from checkpoint
    checkpoint = torch.load(args.checkpoint_filepath, map_location=run_args.device)
    model.load_state_dict(checkpoint['model_state_dict'])

    # Optionally compile model
    if run_args.compile:
        assert run_args.device.type == "cuda", f"torch.compile() with Triton backend only runs on CUDA compatible devices."
        model = torch.compile(model, backend="inductor")  # type: ignore

    # Load the tokenizer
    if args.tokenizer == "gopilot":
        tokenizer = GopilotTokenizer.from_file(args.tokenizer_cf)
    else:
        tokenizer = HuggingFaceTokenizer.from_file(args.tokenizer_cf)

    # Load the dataset
    dataset = GopilotFineTuningDataset(args.dataset_filepath, tokenizer)
