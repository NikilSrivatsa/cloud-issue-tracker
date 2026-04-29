output "public_ip" {
  description = "Public IP address of the deployed application."
  value       = aws_instance.app.public_ip
}

output "application_url" {
  description = "HTTP URL of the deployed application."
  value       = "http://${aws_instance.app.public_ip}"
}
