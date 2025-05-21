# On-Prem Model Garden Usage Guide

This guide is designed for application developers who need to interact with the on-prem model garden. It provides instructions on how to access the service and make API calls to various endpoints.

## Prerequisites

- **VPN Access Required**: All endpoints are only accessible when connected to the VPN.

## Dashboard Access

The Ray dashboard is accessible at:
```
https://ray.revelare.io/#/overview
```

### Useful Dashboard Features

- **Serve Tab**: Click on either deployment to view logs of the calls you make against the endpoint. This is particularly useful for debugging and monitoring your API interactions.

## API Endpoints

### Embedding Service

Use this endpoint to generate embeddings for text inputs:

```bash
curl https://ray.revelare.io/embed/v1/embeddings -H "Content-Type: application/json" -d '{"model":"Linq-AI-Research/Linq-Embed-Mistral","input":"This is a sample text to create embeddings for."}'
```

### Chat Completion Service

#### Basic Chat (without tools)

```bash
curl https://ray.revelare.io/chat/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"meta-llama/Llama-3.1-8B-Instruct","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"Provide a brief sentence describing the Ray open-source project."}],"temperature":0.7}'
```

#### Chat with Tool Calling

```bash
curl https://ray.revelare.io/chat/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"meta-llama/Llama-3.1-8B-Instruct","tools":[{"type":"function","function":{"name":"get_current_weather","description":"Return the current weather for a given city.","parameters":{"type":"object","properties":{"location":{"type":"string","description":"City and state, e.g. Seattle, WA"},"unit":{"type":"string","enum":["celsius","fahrenheit"],"description":"Temperature unit"}},"required":["location"]}}}],"messages":[{"role":"system","content":"You are a helpful weather assistant."},{"role":"user","content":"What'\''s the weather in Seattle right now?"}],"tool_choice":"auto","temperature":0.0}'
```

## Available Models

The on-prem model garden supports various models including:

- **Embedding Models**: 
  - `Linq-AI-Research/Linq-Embed-Mistral`

- **Chat Models**:
  - `meta-llama/Llama-3.1-8B-Instruct`

## Model Limitations

### Reduced Context Window

To ensure stability on our on-prem GPU hardware, we've had to configure the Llama 3.1 model with a reduced context length:

| Feature | Default Llama 3.1 | Our On-Prem Deployment |
|---------|-------------------|------------------------|
| Max context length | 131,072 tokens (128k) | 30,000 tokens (30k) |
| Prompt + generation | Up to 128k | Up to 30k |

### Impact on Usage

This configuration change means:

- If your prompt history + completion exceeds 30,000 tokens, the request will fail or be truncated
- You won't benefit from the full long-context capabilities that Llama 3.1 normally offers
- For most standard chat use cases (<10k tokens), this 30k limit is still sufficient

### Why This Limitation Exists

- The limitation was necessary to fit the model on our available GPU hardware
- This trade-off reduced maximum context length in exchange for deployment stability
- The model's weights and core capabilities remain unchanged, only the context window is affected

### Best Practices

- Monitor your prompt sizes to avoid hitting the 30k token limit
- For long-running conversations, consider implementing a summarization or context management strategy
- If you need to process very long documents, break them into smaller chunks

## Troubleshooting

If you encounter issues when making API calls:

1. Verify you're connected to the VPN
2. Check the logs in the Ray dashboard's Serve tab
3. Ensure your request format matches the examples provided
