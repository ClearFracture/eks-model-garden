### Create cluster
- **gpu-nodegroup** - is for worker nodes containing llms
```bash
eksctl create cluster -f eks-cluster/clear-fracture-public-cluster.yaml
```

### Add CPU nodegroup for Ray Head Node
```bash
eksctl create nodegroup -f eks-cluster/ray-head-nodegroup.yaml
```

### Add GPU nodegroup for Ray Worker Node
- A g5.12xlarge costs $5.672 per hour
- NVIDIA A10G Tensor Core GPU
```bash
eksctl create nodegroup -f eks-cluster/ray-worker-nodegroup.yaml
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
  # -f helm/kuberay-operator-values.yaml # no longer need to deploy kuberay-operator on specific node.
```

### Apply patches to ray service
```bash
kubectl apply -k ray-model-garden/
```

### Build ray-vllm image
```bash
docker build -t 891377002699.dkr.ecr.us-east-2.amazonaws.com/clearfracture/ray-vllm:latest ray-vllm-cu121
```

### Ray Dashboard
```bash
kubectl port-forward <head node> 8265:8265
```
http://localhost:8265/#/overview


### curl from local machine
```bash
kubectl port-forward svc/ray-model-garden-serve-svc 8000
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


### test the bedrock proxy
```bash
kubectl port-forward svc/bedrock-proxy-svc 8000:8000
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "How can I build a Kubernetes operator?",
    "model_id": "meta.llama3-8b-instruct-v1:0"
  }'
```