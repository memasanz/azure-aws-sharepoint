# -----------------------------------------------------------------------------
# Cognito Identity Pool — the "token bridge" (PRODUCT-SPEC.md §7.1)
# Uses DEVELOPER-authenticated identities: the Lambda mints tokens with its IAM
# role via GetOpenIdTokenForDeveloperIdentity. No unauthenticated identities.
# -----------------------------------------------------------------------------
resource "aws_cognito_identity_pool" "bridge" {
  identity_pool_name               = var.identity_pool_name
  allow_unauthenticated_identities = false
  developer_provider_name          = var.developer_provider_name
}

# -----------------------------------------------------------------------------
# Lambda execution role — least privilege: logs + mint-token on THIS pool only.
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.lambda_function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "mint_token" {
  statement {
    sid       = "MintCognitoOpenIdToken"
    effect    = "Allow"
    actions   = ["cognito-identity:GetOpenIdTokenForDeveloperIdentity"]
    resources = [aws_cognito_identity_pool.bridge.arn]
  }
}

resource "aws_iam_role_policy" "mint_token" {
  name   = "mint-cognito-token"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.mint_token.json
}

# -----------------------------------------------------------------------------
# Token-minter Lambda (spike): returns a Cognito JWT.
# -----------------------------------------------------------------------------
data "archive_file" "token_minter" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/token_minter"
  output_path = "${path.module}/build/token_minter.zip"
}

resource "aws_lambda_function" "token_minter" {
  function_name    = var.lambda_function_name
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.token_minter.output_path
  source_code_hash = data.archive_file.token_minter.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      IDENTITY_POOL_ID        = aws_cognito_identity_pool.bridge.id
      DEVELOPER_PROVIDER_NAME = var.developer_provider_name
      DEVELOPER_IDENTIFIER    = var.developer_identifier
    }
  }
}
