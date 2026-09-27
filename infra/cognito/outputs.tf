output "identity_pool_id" {
  description = "Cognito Identity Pool ID — this is the JWT 'aud' claim APIM validates."
  value       = aws_cognito_identity_pool.bridge.id
}

output "identity_pool_arn" {
  description = "Cognito Identity Pool ARN."
  value       = aws_cognito_identity_pool.bridge.arn
}

output "developer_provider_name" {
  description = "Developer provider name used to mint tokens."
  value       = var.developer_provider_name
}

output "token_minter_function_name" {
  description = "Invoke this Lambda to obtain a Cognito JWT for the spike."
  value       = aws_lambda_function.token_minter.function_name
}

output "jwt_issuer" {
  description = "Expected JWT 'iss' claim — pin this in the APIM validate-jwt policy."
  value       = "https://cognito-identity.amazonaws.com"
}
