import boto3
import re
from difflib import SequenceMatcher
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache of available Bedrock models
_model_cache = None
_model_cache_expiry = None
import time

def get_available_bedrock_models(region="us-east-1", force_refresh=False):
    """
    Get available foundation models from Bedrock
    
    Args:
        region: AWS region (ignored, always uses us-east-1)
        force_refresh: Force refresh of model cache
        
    Returns:
        List of model IDs available in Bedrock
    """
    global _model_cache, _model_cache_expiry
    
    # Always use us-east-1 regardless of input
    region = "us-east-1"
    
    # Cache results for 1 hour to avoid excessive API calls
    current_time = time.time()
    if not force_refresh and _model_cache and _model_cache_expiry and current_time < _model_cache_expiry:
        return _model_cache
    
    try:
        client = boto3.client('bedrock', region_name=region)
        response = client.list_foundation_models(byInferenceType="ON_DEMAND")
        models = response['modelSummaries']
        
        # Extract model IDs and cache them
        model_ids = [model["modelId"] for model in models]
        _model_cache = model_ids
        _model_cache_expiry = current_time + 3600  # Cache for 1 hour
        
        logger.info(f"Loaded {len(model_ids)} available Bedrock models from {region}")
        return model_ids
    except Exception as e:
        logger.error(f"Error fetching Bedrock models from {region}: {str(e)}")
        # Return empty list or cached list if available
        return _model_cache or []

def normalize_model_name(model_id):
    """
    Normalize model name for better comparison
    
    Args:
        model_id: Original model ID
        
    Returns:
        Normalized model name for comparison
    """
    # Convert to lowercase
    normalized = model_id.lower()
    
    # Remove version numbers, special characters
    normalized = re.sub(r'[-/:\s_]', '', normalized)
    normalized = re.sub(r'v\d+', '', normalized)
    
    # Remove common prefixes like "meta-llama/" or "meta."
    normalized = re.sub(r'^meta[\.-]?llama[/]?', 'llama', normalized)
    normalized = re.sub(r'^anthropic[\.-]?claude[/]?', 'claude', normalized)
    normalized = re.sub(r'^amazon[\.-]?titan[/]?', 'titan', normalized)
    
    return normalized

def similarity_score(a, b):
    """
    Calculate string similarity between two strings
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        Similarity score between 0 and 1
    """
    return SequenceMatcher(None, a, b).ratio()

def map_to_bedrock_model_id(client_model_id, region="us-east-1"):
    """
    Map a client model ID to the closest matching Bedrock model ID
    
    Args:
        client_model_id: Model ID from client (e.g. "meta-llama/Meta-Llama-3-8B-Instruct")
        region: AWS region (ignored, always uses us-east-1)
        
    Returns:
        Closest matching Bedrock model ID or None if no match found
    """
    # Always use us-east-1 regardless of input
    region = "us-east-1"
    
    # Special case for embedding models
    if "embed" in client_model_id.lower() or "embedding" in client_model_id.lower():
        return "amazon.titan-embed-text-v1"
    
    # Get available Bedrock models
    available_models = get_available_bedrock_models(region)
    if not available_models:
        logger.warning("No available Bedrock models found")
        return None
    
    # Normalize input model ID
    normalized_input = normalize_model_name(client_model_id)
    logger.info(f"Normalized input model '{client_model_id}' to '{normalized_input}'")
    
    # Direct mapping for common models
    direct_mappings = {
        # Llama 3 models
        "llamametallama38binstruct": "meta.llama3-8b-instruct-v1:0",
        "llamallama38binstruct": "meta.llama3-8b-instruct-v1:0",
        "llama38binstruct": "meta.llama3-8b-instruct-v1:0",
        "llamametallama370binstruct": "meta.llama3-70b-instruct-v1:0",
        "llamallama370binstruct": "meta.llama3-70b-instruct-v1:0",
        "llama370binstruct": "meta.llama3-70b-instruct-v1:0",
        
        # Claude models
        "claudeanthropicclaudesonetv2": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claudeclaudesonetv2": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claudesonetv2": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claudesonet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claudeanthropicclaudehaiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claudeclaudehaiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claudehaiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claudeanthropicclaude3opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claudeclaude3opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claudeopus": "anthropic.claude-3-opus-20240229-v1:0",
        
        # Titan models
        "titantextlite": "amazon.titan-text-lite-v1",
        "titantextexpress": "amazon.titan-text-express-v1",
    }
    
    # Check for direct mapping
    if normalized_input in direct_mappings:
        mapped_model = direct_mappings[normalized_input]
        logger.info(f"Direct mapping found: '{client_model_id}' -> '{mapped_model}'")
        return mapped_model
    
    # If no direct mapping, find best match by similarity
    best_match = None
    best_score = 0
    
    for bedrock_model in available_models:
        normalized_bedrock = normalize_model_name(bedrock_model)
        score = similarity_score(normalized_input, normalized_bedrock)
        
        # Prefer models of the same family
        model_family_match = False
        for family in ["llama", "claude", "titan"]:
            if family in normalized_input and family in normalized_bedrock:
                model_family_match = True
                break
        
        if model_family_match:
            score *= 1.5  # Boost score for models in the same family
            
        if score > best_score:
            best_score = score
            best_match = bedrock_model
    
    # Only return if we have a reasonable match
    if best_score > 0.6:
        logger.info(f"Best match for '{client_model_id}' is '{best_match}' with score {best_score:.2f}")
        return best_match
    else:
        logger.warning(f"No good match found for '{client_model_id}', best was '{best_match}' with score {best_score:.2f}")
        
        # Fallback to default models based on name
        if "llama" in normalized_input:
            default = "meta.llama3-8b-instruct-v1:0"
            logger.info(f"Falling back to default Llama model: {default}")
            return default
        elif "claude" in normalized_input:
            default = "anthropic.claude-3-haiku-20240307-v1:0"
            logger.info(f"Falling back to default Claude model: {default}")
            return default
        else:
            default = "meta.llama3-8b-instruct-v1:0"  # Default to Llama 3 8B
            logger.info(f"Falling back to general default model: {default}")
            return default

# For testing
if __name__ == "__main__":
    # Test with some example mappings
    test_models = [
        "meta-llama/Meta-Llama-3-8B-Instruct",
        "meta-llama/Llama-2-70b-chat-hf",
        "anthropic/claude-3-sonnet",
        "anthropic/claude-3-haiku",
        "mistralai/Mistral-7B-Instruct-v0.2",
        "intfloat/e5-mistral-7b-instruct"
    ]
    
    for model in test_models:
        bedrock_model = map_to_bedrock_model_id(model)
        print(f"Client model: {model} -> Bedrock model: {bedrock_model}") 