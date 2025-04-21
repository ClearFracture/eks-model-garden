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
