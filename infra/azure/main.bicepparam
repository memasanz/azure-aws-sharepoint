using './main.bicep'

// Fill these in before deploying.
param apimName = 'sharepoint-bridge-apim'
param publisherEmail = 'you@example.com'
param publisherName = 'SharePoint Bridge'
param sku = 'Developer'

// From AWS Terraform output `identity_pool_id` (safe placeholder until then).
param identityPoolId = 'REPLACE_WITH_COGNITO_IDENTITY_POOL_ID'

// The single allowed Cognito identity id (JWT sub) — from scripts/decode_jwt.py.
param allowedCognitoSub = 'REPLACE_WITH_ALLOWED_COGNITO_SUB'
