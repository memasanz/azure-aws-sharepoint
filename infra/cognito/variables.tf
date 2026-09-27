variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "identity_pool_name" {
  description = "Name of the dedicated Cognito Identity Pool (used by nothing else)."
  type        = string
  default     = "sharepoint-bridge-pool"
}

variable "developer_provider_name" {
  description = <<-EOT
    Developer provider name for developer-authenticated identities. The Lambda
    mints tokens via GetOpenIdTokenForDeveloperIdentity against this provider,
    so no unauthenticated identities are enabled.
  EOT
  type        = string
  default     = "sharepoint-bridge"
}

variable "developer_identifier" {
  description = <<-EOT
    Stable developer user identifier the Lambda supplies. A fixed value yields a
    stable Cognito identity id (the token 'sub'), which APIM pins in Sprint B2.
  EOT
  type        = string
  default     = "aws-sharepoint-reader"
}

variable "lambda_function_name" {
  description = "Name of the token-minter Lambda."
  type        = string
  default     = "sharepoint-bridge-token-minter"
}
