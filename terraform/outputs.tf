output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "kb_id" {
  value = aws_bedrockagent_knowledge_base.main.id
}

output "s3_bucket_name" {
  value = aws_s3_bucket.docs.id
}

output "backend_repo_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "frontend_repo_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}
