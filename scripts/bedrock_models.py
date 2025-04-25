import boto3

client = boto3.client('bedrock', region_name='us-east-1')

response = client.list_foundation_models(
    byInferenceType="ON_DEMAND"
)

models = response['modelSummaries']

print(f'I found {len(models)} available models.')

for model in models:
    print(f'- {model["modelId"]}') 