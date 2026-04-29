pipeline {
  agent any

  parameters {
    string(name: 'AWS_KEY_NAME', defaultValue: 'cloud-project-key', description: 'Existing AWS EC2 key pair name')
    string(name: 'ADMIN_CIDR', defaultValue: '0.0.0.0/0', description: 'CIDR allowed for SSH. For demo use your-public-ip/32.')
  }

  environment {
    AWS_DEFAULT_REGION = 'ap-south-1'
    TF_DIR = 'terraform'
    IMAGE_NAME = 'cloud-issue-tracker:latest'
  }

  stages {
    stage('Checkout From Git') {
      steps {
        checkout scm
      }
    }

    stage('Build Docker Image') {
      steps {
        sh 'docker build --platform linux/amd64 -t $IMAGE_NAME .'
        sh 'docker save $IMAGE_NAME -o cloud-issue-tracker.tar'
      }
    }

    stage('Provision AWS Infrastructure') {
      steps {
        dir("${TF_DIR}") {
          sh 'terraform init -input=false'
          sh 'terraform apply -auto-approve -input=false -var="key_name=$AWS_KEY_NAME" -var="admin_cidr=$ADMIN_CIDR"'
        }
      }
    }

    stage('Deploy Application') {
      steps {
        script {
          def publicIp = sh(
            script: "cd ${TF_DIR} && terraform output -raw public_ip",
            returnStdout: true
          ).trim()

          sshagent(credentials: ['aws-ec2-ssh-key']) {
            sh "scp -o StrictHostKeyChecking=no cloud-issue-tracker.tar ubuntu@${publicIp}:/tmp/cloud-issue-tracker.tar"
            sh "scp -o StrictHostKeyChecking=no scripts/deploy.sh ubuntu@${publicIp}:/tmp/deploy.sh"
            sh "ssh -o StrictHostKeyChecking=no ubuntu@${publicIp} 'chmod +x /tmp/deploy.sh && sudo /tmp/deploy.sh'"
          }
        }
      }
    }
  }

  post {
    success {
      echo 'Deployment completed. Open the EC2 public IP in a browser.'
    }
  }
}
