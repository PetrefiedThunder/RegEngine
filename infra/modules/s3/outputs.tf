output "raw_bucket_name" {
  description = "Raw data bucket name"
  value       = aws_s3_bucket.raw.id
}

output "raw_bucket_arn" {
  description = "Raw data bucket ARN"
  value       = aws_s3_bucket.raw.arn
}

output "processed_bucket_name" {
  description = "Processed data bucket name"
  value       = aws_s3_bucket.processed.id
}

output "processed_bucket_arn" {
  description = "Processed data bucket ARN"
  value       = aws_s3_bucket.processed.arn
}
