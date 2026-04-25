# =====================================================================
# Variáveis do Terraform - Detector de Anomalias
# =====================================================================

variable "aws_region" {
  description = "Região AWS para deploy"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome do projeto (usado como prefixo em recursos)"
  type        = string
  default     = "anomaly-detector"
}

variable "environment" {
  description = "Ambiente (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "CIDR da VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDRs das subnets públicas"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs das subnets privadas"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "availability_zones" {
  description = "Zonas de disponibilidade"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# --- ECS ---
variable "container_image" {
  description = "Imagem Docker no ECR (ex: ACCOUNT.dkr.ecr.REGION.amazonaws.com/repo:tag)"
  type        = string
  default     = "anomaly-detector:latest"
}

variable "container_cpu" {
  description = "CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "container_memory" {
  description = "Memória em MB"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Número desejado de tasks rodando"
  type        = number
  default     = 2
}

variable "container_port" {
  description = "Porta do container FastAPI"
  type        = number
  default     = 8000
}

# --- RDS ---
variable "db_instance_class" {
  description = "Classe da instância RDS"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Storage alocado em GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Nome do banco de dados"
  type        = string
  default     = "anomaly_db"
}

variable "db_username" {
  description = "Usuário master do RDS"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "Senha do banco (use SSM Parameter Store em produção real)"
  type        = string
  sensitive   = true
}
