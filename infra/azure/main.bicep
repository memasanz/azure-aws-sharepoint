// -----------------------------------------------------------------------------
// Azure side (Sprint B1): API Management with a system-assigned managed identity,
// the SharePoint Reader API, and the validate-jwt -> managed-identity -> Graph
// policy. Deployable independently of the AWS side.
//
// After deploy:
//   1. Grant the APIM managed identity a Selected read role on your site
//      (scripts/grant_selected_read.py, using output `apimPrincipalId`).
//   2. Point the reader Lambda at output `readEndpoint`.
// -----------------------------------------------------------------------------

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Globally unique APIM service name.')
param apimName string

@description('Publisher email shown on the APIM instance.')
param publisherEmail string

@description('Publisher/organization name shown on the APIM instance.')
param publisherName string

@description('APIM SKU. Developer is fine for PoC; use Standard/Premium for prod.')
@allowed([
  'Developer'
  'Basic'
  'Standard'
  'Premium'
])
param sku string = 'Developer'

@description('Cognito Identity Pool ID from the AWS Terraform output `identity_pool_id`. This is the JWT `aud` claim APIM validates. Placeholder is safe to deploy; update before the AWS side is wired.')
param identityPoolId string = 'REPLACE_WITH_COGNITO_IDENTITY_POOL_ID'

@description('The single allowed Cognito identity id (JWT `sub`) — the B2 trust pin. Get it from scripts/decode_jwt.py after the AWS side mints a token. Placeholder is safe to deploy; the reader will 401 until this is set correctly.')
param allowedCognitoSub string = 'REPLACE_WITH_ALLOWED_COGNITO_SUB'

resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: apimName
  location: location
  sku: {
    name: sku
    capacity: 1
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
  }
}

resource identityPoolNamedValue 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'identity-pool-id'
  properties: {
    displayName: 'identity-pool-id'
    value: identityPoolId
    secret: false
  }
}

resource allowedSubNamedValue 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'allowed-cognito-sub'
  properties: {
    displayName: 'allowed-cognito-sub'
    value: allowedCognitoSub
    secret: false
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apim
  name: 'sharepoint'
  properties: {
    displayName: 'SharePoint Reader'
    path: 'sharepoint'
    protocols: [
      'https'
    ]
    subscriptionRequired: false
  }
}

resource readOperation 'Microsoft.ApiManagement/service/apis/operations@2023-05-01-preview' = {
  parent: api
  name: 'read-folder'
  properties: {
    displayName: 'Read folder'
    method: 'GET'
    urlTemplate: '/read'
    description: 'Lists (reads) children of a SharePoint folder via Microsoft Graph.'
  }
}

resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-05-01-preview' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('../../apim/policy.xml')
  }
  dependsOn: [
    identityPoolNamedValue
    allowedSubNamedValue
    readOperation
  ]
}

@description('Object (principal) ID of the APIM system-assigned managed identity. Pass this to scripts/grant_selected_read.py.')
output apimPrincipalId string = apim.identity.principalId

@description('APIM gateway base URL.')
output gatewayUrl string = apim.properties.gatewayUrl

@description('Full read endpoint the reader Lambda calls.')
output readEndpoint string = '${apim.properties.gatewayUrl}/sharepoint/read'
