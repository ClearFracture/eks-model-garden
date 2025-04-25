from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import boto3
import json
import os
import logging
from model_mapper import map_to_bedrock_model_id

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Hardcode region to us-east-1 regardless of environment variable
region = "us-east-1"
logger.info(f"Using hardcoded AWS region: {region}")
bedrock = boto3.client("bedrock-runtime", region_name=region)

class Message(BaseModel):
    role: str
    content: str

class ChatData(BaseModel):
    model: str = Field(..., description="Model ID to use")
    messages: List[Message] = Field(..., description="Messages to send to the model")
    temperature: float = 0.7

class DaprRequest(BaseModel):
    operation: str
    data: ChatData

class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    model_id: Optional[str] = "meta.llama3-8b-instruct-v1:0"
    # For Dapr binding compatibility - these fields will be populated from the binding request
    operation: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class EmbedRequest(BaseModel):
    input: str
    model_id: str = "amazon.titan-embed-text-v1"  # default

@app.post("/chat")
async def chat(request: Request):
    try:
        # Parse the raw JSON
        raw_data = await request.json()
        logger.info(f"Received request: {raw_data}")
        
        # Extract prompt from different possible formats
        prompt = ""
        model_id = "meta.llama3-8b-instruct-v1:0"
        
        # Check for messages format (unwrapped Dapr format)
        if "messages" in raw_data and isinstance(raw_data["messages"], list) and len(raw_data["messages"]) > 0:
            logger.info("Detected unwrapped messages format")
            messages = raw_data["messages"]
            
            if isinstance(messages[0], dict) and "content" in messages[0]:
                prompt = messages[0]["content"]
                logger.info(f"Extracted prompt from messages: '{prompt[:50]}...'")
            
            # Get model ID if present
            if "model" in raw_data:
                model_id = raw_data["model"]
        
        # Check for Dapr binding format (shouldn't happen with Dapr sidecar, but kept for direct testing)
        elif "operation" in raw_data and "data" in raw_data:
            logger.info("Detected Dapr binding format")
            data = raw_data.get("data", {})
            model_id = data.get("model", model_id)
            
            messages = data.get("messages", [])
            if messages and isinstance(messages, list) and len(messages) > 0:
                message = messages[0]
                if isinstance(message, dict):
                    prompt = message.get("content", "")
                    logger.info(f"Extracted prompt from Dapr binding: '{prompt[:50]}...'")
        
        # Check for direct API call format 
        elif "prompt" in raw_data:
            logger.info("Detected direct API call format")
            prompt = raw_data.get("prompt", "")
            model_id = raw_data.get("model_id", model_id)
            logger.info(f"Extracted from direct call: model_id={model_id}, prompt={prompt[:50]}...")
        
        # Validate required fields
        if not prompt:
            error_msg = "Missing prompt in request"
            logger.error(f"{error_msg}. Raw data: {raw_data}")
            return {"error": error_msg}
        
        # Map the client model ID to a Bedrock model ID
        original_model_id = model_id
        bedrock_model_id = map_to_bedrock_model_id(model_id, region=region)
        
        if not bedrock_model_id:
            logger.error(f"Could not map model '{model_id}' to a Bedrock model")
            # Fallback to default model
            bedrock_model_id = "meta.llama3-8b-instruct-v1:0"
        
        logger.info(f"Mapped model ID '{original_model_id}' to Bedrock model '{bedrock_model_id}'")
        
        if bedrock_model_id.startswith("meta.llama"):
            # Meta Llama models expect a 'prompt' field
            body = {
                "prompt": prompt,
                "temperature": 0.7
            }
        else:
            # Claude and other models use 'messages' format
            body = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        
        try:
            response = bedrock.invoke_model(
                modelId=bedrock_model_id,
                contentType="application/json",
                body=json.dumps(body)
            )
            raw_output = json.loads(response["body"].read())
            logger.info(f"Received raw output from Bedrock: {raw_output}")
            
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
            logger.info(f"Returning normalized response: {normalized}")
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
    except Exception as e:
        logger.exception(f"Unexpected error processing request: {str(e)}")
        return {"error": f"Error processing request: {str(e)}"}


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
async def embed(request: Request):
    try:
        # Parse the request JSON
        raw_data = await request.json()
        logger.info(f"Received embedding request: {raw_data}")
        
        # Check if this is a Dapr binding request format
        if "operation" in raw_data and "data" in raw_data:
            # Handle Dapr binding format
            logger.info("Detected Dapr binding format for embedding")
            model_id = raw_data["data"].get("model", "amazon.titan-embed-text-v1")
            
            # Extract input text
            input_text = raw_data["data"].get("input", "")
            if not input_text:
                # Try to find other common field names
                input_text = raw_data["data"].get("text", "")
                if not input_text:
                    input_text = raw_data["data"].get("inputText", "")
                    if not input_text:
                        input_text = str(raw_data["data"])  # Last resort
                
            logger.info(f"Extracted from Dapr: model_id={model_id}, input_text={input_text[:30]}...")
        else:
            # Handle direct API call format
            input_text = raw_data.get("input", "")
            model_id = raw_data.get("model_id", "amazon.titan-embed-text-v1")
            logger.info(f"Direct API call: model_id={model_id}, input_text={input_text[:30]}...")
        
        # Validate required fields
        if not input_text:
            error_msg = "Missing input text in request"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Map the client model ID to a Bedrock embedding model ID
        original_model_id = model_id
        bedrock_model_id = map_to_bedrock_model_id(model_id, region=region)
        
        if not bedrock_model_id:
            logger.error(f"Could not map embedding model '{model_id}' to a Bedrock model")
            # Fallback to default embedding model
            bedrock_model_id = "amazon.titan-embed-text-v1"
        
        logger.info(f"Mapped embedding model ID '{original_model_id}' to Bedrock model '{bedrock_model_id}'")
        
        try:
            body = {"inputText": input_text}
            response = bedrock.invoke_model(
                modelId=bedrock_model_id,
                contentType="application/json",
                body=json.dumps(body)
            )
            raw_output = json.loads(response["body"].read())
            logger.info(f"Received raw embedding output from Bedrock (showing length only): {len(str(raw_output))} chars")
            
            # Format embedding response to be more consistent
            if "embedding" in raw_output:
                embeddings = raw_output["embedding"]
            elif "embeddings" in raw_output:
                embeddings = raw_output["embeddings"]
            else:
                # Try to extract from common patterns
                embeddings = raw_output.get("data", [{}])[0].get("embedding", [])
            
            logger.info(f"Extracted embeddings of length: {len(embeddings)}")
            
            embedding_response = {
                "data": [{"embedding": embeddings}],
                "model": original_model_id  # Return the original model ID for compatibility
            }
            
            return embedding_response
        except Exception as e:
            logger.error(f"Error invoking Bedrock embedding model: {str(e)}")
            return {
                "error": str(e),
                "model": original_model_id
            }
    except Exception as e:
        logger.exception(f"Unexpected error processing embedding request: {str(e)}")
        return {"error": f"Error processing embedding request: {str(e)}"}

@app.get("/health")
def health():
    return {"status": "ok"}
