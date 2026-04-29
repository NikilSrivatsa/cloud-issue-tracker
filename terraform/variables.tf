variable "aws_region" {
  description = "AWS region where the EC2 instance will be created."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name used for AWS resources."
  type        = string
  default     = "cloud-issue-tracker"
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Existing AWS EC2 key pair name used by Jenkins for SSH."
  type        = string
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH into the instance. Use your public IP with /32."
  type        = string
}
