from fastapi import FastAPI
from pydantic import BaseModel
import boto3
import json
import os
import logging
from model_mapper import map_to_bedrock_model_id

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Use environment variable for region if available, default to us-east-1
region = os.environ.get("AWS_REGION", "us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name=region)

class ChatRequest(BaseModel):
    prompt: str
    model_id: str = "meta.llama3-8b-instruct-v1:0"  # default

class EmbedRequest(BaseModel):
    input: str
    model_id: str = "amazon.titan-embed-text-v1"  # default

@app.post("/chat")
def chat(req: ChatRequest):
    # Map the client model ID to a Bedrock model ID
    original_model_id = req.model_id
    bedrock_model_id = map_to_bedrock_model_id(req.model_id, region=region)
    
    if not bedrock_model_id:
        logger.error(f"Could not map model '{req.model_id}' to a Bedrock model")
        # Fallback to default model
        bedrock_model_id = "meta.llama3-8b-instruct-v1:0"
    
    logger.info(f"Mapped model ID '{original_model_id}' to Bedrock model '{bedrock_model_id}'")
    
    if bedrock_model_id.startswith("meta.llama"):
        # Meta Llama models expect a 'prompt' field
        body = {
            "prompt": req.prompt,
            "temperature": 0.7
        }
    else:
        # Claude and other models use 'messages' format
        body = {
            "messages": [{"role": "user", "content": req.prompt}],
            "temperature": 0.7
        }
    
    try:
        response = bedrock.invoke_model(
            modelId=bedrock_model_id,
            contentType="application/json",
            body=json.dumps(body)
        )
        raw_output = json.loads(response["body"].read())
        
        # Normalize to OpenAI-style response
        normalized = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": extract_content(raw_output, bedrock_model_id)
                    }
                }
            ],
            "model": original_model_id  # Return the original model ID for compatibility
        }
        return normalized
    except Exception as e:
        logger.error(f"Error invoking Bedrock model: {str(e)}")
        # Return a structured error response
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"Error: Could not process request with model {bedrock_model_id}. {str(e)}"
                    }
                }
            ],
            "model": original_model_id,
            "error": str(e)
        }


def extract_content(output, model_id):
    """Extract content from different model responses"""
    try:
        # Llama models
        if model_id.startswith("meta.llama"):
            if "generation" in output:
                return output["generation"]
            elif "completion" in output:
                return output["completion"]
        
        # Claude models
        elif model_id.startswith("anthropic.claude"):
            if "completion" in output:
                return output["completion"]
            elif "content" in output and isinstance(output["content"], list):
                # Extract text from content array
                texts = [item.get("text", "") for item in output["content"] if item.get("type") == "text"]
                return "".join(texts)
            elif "content" in output:
                return output["content"]
        
        # Amazon Titan models
        elif model_id.startswith("amazon.titan"):
            if "results" in output and len(output["results"]) > 0:
                return output["results"][0].get("outputText", "")
            elif "outputText" in output:
                return output["outputText"]
        
        # Check common patterns across models
        if "generation" in output:
            return output["generation"]
        elif "outputs" in output and len(output["outputs"]) > 0:
            if isinstance(output["outputs"][0], dict):
                return output["outputs"][0].get("text", "")
            else:
                return str(output["outputs"][0])
        elif "content" in output:
            if isinstance(output["content"], list):
                texts = []
                for item in output["content"]:
                    if isinstance(item, dict) and "text" in item:
                        texts.append(item["text"])
                    elif isinstance(item, str):
                        texts.append(item)
                return "".join(texts)
            return output["content"]
        elif "text" in output:
            return output["text"]
        
        # Last resort: Return the raw output as string
        return str(output)
    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return f"Error extracting response content: {str(e)}"

@app.post("/embed")
def embed(req: EmbedRequest):
    # Map the client model ID to a Bedrock embedding model ID
    original_model_id = req.model_id
    bedrock_model_id = map_to_bedrock_model_id(req.model_id, region=region)
    
    if not bedrock_model_id:
        logger.error(f"Could not map embedding model '{req.model_id}' to a Bedrock model")
        # Fallback to default embedding model
        bedrock_model_id = "amazon.titan-embed-text-v1"
    
    logger.info(f"Mapped embedding model ID '{original_model_id}' to Bedrock model '{bedrock_model_id}'")
    
    try:
        body = {"inputText": req.input}
        response = bedrock.invoke_model(
            modelId=bedrock_model_id,
            contentType="application/json",
            body=json.dumps(body)
        )
        raw_output = json.loads(response["body"].read())
        
        # Format embedding response to be more consistent
        if "embedding" in raw_output:
            embeddings = raw_output["embedding"]
        elif "embeddings" in raw_output:
            embeddings = raw_output["embeddings"]
        else:
            # Try to extract from common patterns
            embeddings = raw_output.get("data", [{}])[0].get("embedding", [])
        
        return {
            "data": [{"embedding": embeddings}],
            "model": original_model_id  # Return the original model ID for compatibility
        }
    except Exception as e:
        logger.error(f"Error invoking Bedrock embedding model: {str(e)}")
        return {
            "error": str(e),
            "model": original_model_id
        }

@app.get("/health")
def health():
    return {"status": "ok"}
