### Create cluster
- **gpu-nodegroup** - is for worker nodes containing llms
```bash
eksctl create cluster \
  --name=clear-fracture-public-cluster \
  --region=us-east-2 \
  --version=1.32 \
  --nodegroup-name=gpu-nodegroup \
  --node-type=g5.8xlarge \
  --nodes=1 \
  --nodes-min=1 \
  --nodes-max=4 \
  --ssh-access \
  --ssh-public-key keith-laptop \
  --dry-run
```
### Add CPU nodegroup for Ray Head Node
```bash
eksctl create nodegroup \
  --cluster=clear-fracture-public-cluster \
  --name=ray-head \
  --instance-types=m5.large \
  --nodes=1 \
  --nodes-min=1 \
  --nodes-max=1 \
  --ssh-access \
  --ssh-public-key keith-laptop \
  --dry-run
```

### Add GPU nodegroup for Ray Worker Node
- A g5.12xlarge costs $5.672 per hour
- NVIDIA A10G Tensor Core GPU
```bash
eksctl create nodegroup \
  --cluster=clear-fracture-public-cluster \
  --name=ray-worker \
  --instance-types=g5.12xlarge \
  --nodes=1 \
  --nodes-min=1 \
  --nodes-max=4 \
  --ssh-access \
  --ssh-public-key keith-laptop \
  --dry-run
```

### Add hugging face access token
```bash
export HF_TOKEN=<your HuggingFace token>
./scripts/create-hf-secret.sh
```

### Deploy kuberay-operator
```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm
helm repo update
helm upgrade --install kuberay-operator kuberay/kuberay-operator \
  --version 1.3.0 \
  -f helm/kuberay-operator-values.yaml
```


### Apply patches to ray service
```bash
kubectl apply -k ray-service‑overlay/
```
### Build ray-vllm image
```bash
docker build -t 891377002699.dkr.ecr.us-east-2.amazonaws.com/clearfracture/ray-vllm:latest ray-vllm-cu121
```

### Ray Dashboard
```bash
kubectl port-forward <head node> 8265:8265
```
http://localhost:8265/#/serve/applications/llm/VLLMDeployment?replicaId=0v521ryh


### curl from local machine
```bash
kubectl port-forward svc/llama-3-8b-serve-svc 8000
```

### test query for chat
```bash
curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
      "model": "meta-llama/Meta-Llama-3-8B-Instruct",
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Provide a brief sentence describing the Ray open-source project."}
      ],
      "temperature": 0.7
    }'
```

### test query for embedding
```bash
curl http://localhost:8000/embed/v1/embeddings -H "Content-Type: application/json" -d '{
  "model": "intfloat/e5-mistral-7b-instruct",
  "input": "This is a sample text to create embeddings for."
}'
```

### associate eks with iam oidc provider
```bash
eksctl utils associate-iam-oidc-provider \
    --region us-east-2 \
    --cluster clear-fracture-public-cluster \
    --approve
```


### add iam role for bedrock access
```bash
eksctl create iamserviceaccount \
  --name bedrock-invoke-sa \
  --namespace default \
  --cluster clear-fracture-public-cluster \
  --attach-policy-arn arn:aws:iam::891377002699:policy/BedrockInvokePolicy \
  --approve
```