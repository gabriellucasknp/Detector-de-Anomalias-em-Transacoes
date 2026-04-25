# =====================================================================
# Outputs do Terraform
# =====================================================================

output "alb_dns_name" {
  description = "DNS público do Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "URL completa da aplicação"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecr_repository_url" {
  description = "URL do repositório ECR para push da imagem Docker"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "Nome do cluster ECS"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Nome do serviço ECS"
  value       = aws_ecs_service.app.name
}

output "rds_endpoint" {
  description = "Endpoint do RDS MySQL"
  value       = aws_db_instance.mysql.address
  sensitive   = true
}

output "rds_port" {
  description = "Porta do RDS"
  value       = aws_db_instance.mysql.port
}

output "cloudwatch_log_group" {
  description = "Log group do CloudWatch"
  value       = aws_cloudwatch_log_group.app.name
}

output "vpc_id" {
  description = "ID da VPC criada"
  value       = aws_vpc.main.id
}
