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
  --ssh-public-key keith-laptop
```
### Add CPU nodegroup for Ray Head Node
```bash
eksctl create nodegroup \
  --cluster=clear-fracture-public-cluster \
  --name=ray-head \ 
  --instance-types=m5.large \
  --nodes=1
  --nodes-min=1
  --nodes-max=1
  --ssh-access
  --ssh-public-key keith-laptop
```
