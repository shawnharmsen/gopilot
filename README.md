# GoPilot

GoPilot is a small language model trained exclusively on Go code.

## Installation

You need to have `conda` and `go` installed on your machine. You can install the necessary dependencies using `conda` and the provided `environment_cpu.yml` (choose `environment_cuda.yml` when running CUDA).

Build the Go tokenizer binary:

```bash
# Linux, MacOS
go build -o tokenizer/libgotok.so -buildmode=c-shared ./tokenizer/libgotok.go
# Windows
go build -o tokenizer/libgotok.dll -buildmode=c-shared ./tokenizer/libgotok.go
```

## Usage

### Pre-Training

A CUDA Docker image is made available. Here are the required parameters.

```bash
docker run \
    -d \
    --gpus '"device=0"' \
    --env AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    --env AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    --env AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION \
    --env NEPTUNE_API_TOKEN=$NEPTUNE_API_TOKEN \
    --cpus 8 \
    --memory 24g \
    ghcr.io/rojas-diego/gopilot:latest \
    python train.py --model model/config/gopilot.yml --tokenizer tokenizer/config/go-scanner-bpe-base.json ----dataset datasets/the-stack-dedup-v1.2/base --gradient-accumulation-steps 64 --batch-size 8 --warmup 1000 --lr 0.001 --training-budget-secs 3600 --device cuda --neptune --compile
```

### Inference Server

The inference server is a simple HTTP server that hosts the model and exposes a `/complete` endpoint to submit samples to auto-complete.

```
python inference_server.py --help
```

### VSCode Extension

To use the VSCode extension you must run up the inference server and load the VSCode extension by running the VSCode command "Developer: Install Extension From Location" and specifying the `vscode` folder. Then, you can invoke the "Gopilot: Auto Complete Code" command.

## Repository Structure

| Location                      | Description                                                                 |
| ----------------------------- | --------------------------------------------------------------------------- |
| `flame`                       | Python library to simplify training deep learning models using PyTorch      |
| `dataset`                     | The gopilot Transformer model and objectives                                |
| `model`                       | Implementation of a Go specific tokenizer                                   |
| `tokenizer`                   | Processing jobs and utilities for the dataset used for pre-training Gopilot |
| `environment_{cpu\|cuda}.yml` | List of dependencies. Install with `conda` or `mamba`.                      |
