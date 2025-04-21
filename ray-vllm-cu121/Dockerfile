FROM rayproject/ray:2.42.1-py311-gpu

ARG TORCH_VER=2.5.0+cu121
ARG EXTRA_INDEX=https://download.pytorch.org/whl/cu121

# Install torch first (wheel has cuda 12.1)
RUN pip install --no-cache-dir --extra-index-url ${EXTRA_INDEX} \
        torch==${TORCH_VER}

# Then vLLM **without** --no-deps so it can upgrade torch when needed
RUN pip install --no-cache-dir vllm==0.8.4

# Install the rest of the packages
RUN pip install --no-cache-dir \
    transformers==4.51.1 \
    "huggingface_hub>=0.30,<1.0" \
    accelerate \
    einops

# Sanity check script to verify installed versions
COPY <<EOF /opt/version_check.py
import ray
import vllm
import torch
import transformers
import huggingface_hub
import accelerate
import einops

print(f"Ray version: {ray.__version__}")
print(f"vLLM version: {vllm.__version__}")
print(f"PyTorch version: {torch.__version__}")
print(f"Transformers version: {transformers.__version__}")
print(f"Huggingface Hub version: {huggingface_hub.__version__}")
print(f"Accelerate version: {accelerate.__version__}")
print(f"Einops version: {einops.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
EOF

# Keep the default entrypoint from the base image
# ENTRYPOINT ["/usr/bin/tini","--","/opt/conda/bin/ray"] 