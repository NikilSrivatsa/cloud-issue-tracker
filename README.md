# Cloud Issue Tracker

Major Project submission using AWS Cloud, Git, Jenkins, Docker, and Terraform.

## Project Summary

CloudOps Issue Center is a dynamic Flask web application that lets users create, update, filter, search, and delete operational issue records. Data is stored in SQLite and persisted through a Docker volume on the AWS EC2 instance.

## Advanced App Features

- Dashboard metrics for total, open, in-progress, critical, and resolved tickets
- Search by title, owner, category, or description
- Filters for status, priority, and environment
- Ticket fields for owner, priority, environment, category, due date, and description
- Recent activity panel based on ticket updates
- Health-check API endpoint at `/health`

## Requirement Mapping

| Requirement | Implemented By |
| --- | --- |
| Team size 2 | Clear module split for App Developer and DevOps Engineer |
| AWS Cloud | Terraform provisions an EC2 instance and security group |
| Git | Repository stores app, infrastructure, and pipeline code |
| Jenkins | `Jenkinsfile` automates checkout, build, provision, and deployment |
| Terraform/Ansible/Docker/Kubernetes | Docker and Terraform are included |
| One-click automation | Jenkins `Build Now` runs the full deployment pipeline |
| Dynamic application | Flask app supports CRUD operations with SQLite persistence |

## Architecture

```text
Developer Pushes Code
        |
        v
GitHub Repository
        |
        v
Jenkins Pipeline
        |
        +--> Docker builds Flask app image
        |
        +--> Terraform provisions AWS EC2
        |
        +--> Jenkins copies image to EC2 over SSH
        |
        v
Docker container runs app on AWS EC2 port 80
```

## Team Work Split

| Member | Responsibility |
| --- | --- |
| Member 1 | Flask app, HTML/CSS UI, SQLite CRUD functionality |
| Member 2 | Dockerfile, Terraform AWS setup, Jenkins pipeline, deployment demo |

## Local Run

```bash
docker compose up --build
```

Open:

```text
http://localhost:5001
```

## AWS Setup

1. Create or use an existing AWS EC2 key pair in the target region.
2. Install Jenkins with these tools available on the Jenkins agent:
   - Git
   - Docker
   - Terraform
   - AWS CLI or AWS environment credentials
3. Add AWS credentials to Jenkins using environment variables or an IAM role.
4. Add the EC2 private key in Jenkins credentials as:

```text
aws-ec2-ssh-key
```

5. Copy the Terraform variable example:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

6. Edit `terraform/terraform.tfvars`:

```hcl
key_name   = "your-existing-aws-keypair-name"
admin_cidr = "YOUR_PUBLIC_IP/32"
```

## One-Click Deployment Flow

After the repository is connected to Jenkins:

1. Click `Build Now` in Jenkins.
2. Jenkins pulls the latest code from GitHub.
3. Jenkins builds the Docker image.
4. Jenkins runs Terraform to provision AWS EC2 infrastructure.
5. Jenkins copies the Docker image and deployment script to EC2.
6. Jenkins starts the application container on port 80.
7. Open the Terraform output public IP in a browser.

## Useful Commands

Format Terraform:

```bash
terraform -chdir=terraform fmt
```

Destroy AWS resources after demo:

```bash
terraform -chdir=terraform destroy
```

Run app without Docker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
python app/app.py
```

## Demo Points

- Create an issue from the web form.
- Change its status from Open to In Progress or Resolved.
- Filter issues by status.
- Delete an issue.
- Show `/health` as a simple API endpoint.
- Show Jenkins console output for Git checkout, Docker build, Terraform apply, and SSH deployment.
