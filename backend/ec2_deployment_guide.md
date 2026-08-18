# EC2 & GitHub Actions Deployment Guide

Yes, you can absolutely create a folder called `backend` in your existing GitHub repository and push all these files there! This is called a "monorepo" setup and is very common. 

This guide walks you through setting up the deployment so that whenever you push changes to the `backend/` folder, GitHub Actions automatically updates your EC2 server.

## Step 1: Set Up Your Repository Structure

Move all the files we just created into a new folder named `backend` inside your existing GitHub repository. Your repository structure should look something like this:

```text
your-existing-repo/
├── existing-code/          # Your other existing code
├── backend/                # Move all the FastAPI files here
│   ├── app/
│   ├── requirements.txt
│   └── ...
└── .github/
    └── workflows/          # GitHub Actions go here
```

## Step 2: Create the GitHub Actions Workflow

GitHub Actions scripts **must** live in a specific folder at the very root of your repository: `.github/workflows/`.

Create a file at `.github/workflows/deploy-backend.yml` and paste the following code:

```yaml
name: Deploy Backend to EC2

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'  # Only trigger if files in the backend folder change!

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Deploy to EC2 via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ec2-user  # Or 'ubuntu' if using Ubuntu EC2
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            # 1. Navigate to the repository folder on the server
            cd /home/ec2-user/your-existing-repo
            
            # 2. Pull the latest code from GitHub
            git pull origin main
            
            # 3. Navigate into the backend folder
            cd backend
            
            # 4. Activate the virtual environment and install dependencies
            source venv/bin/activate
            pip install -r requirements.txt
            
            # 5. Restart the backend service
            sudo systemctl restart hcp-backend
```

## Step 3: Add GitHub Secrets

Your GitHub Action needs permission to log into your EC2 server securely. You need to add these as "Secrets" in your GitHub repository so they aren't exposed to the public.

1. Go to your GitHub repository in the browser.
2. Click **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret** and add the following two secrets:
   - Name: `EC2_HOST` | Secret: *Your EC2 public IP address (e.g., 54.12.34.56)*
   - Name: `EC2_SSH_KEY` | Secret: *The entire contents of your `.pem` SSH key file used to connect to your EC2 instance (including the `BEGIN` and `END` lines).*

## Step 4: First-Time Setup on the EC2 Server

Before GitHub Actions can automate things, you need to set up the server manually one time.

1. **SSH into your EC2 instance:**
   ```bash
   ssh -i your-key.pem ec2-user@your-ec2-ip
   ```

2. **Install system requirements:**
   ```bash
   sudo yum update -y
   sudo yum install git python3.11 -y
   ```

3. **Clone your repository:**
   ```bash
   # You will need to setup a GitHub Deploy Key or Personal Access Token on the server so it can clone private repos
   git clone https://github.com/your-username/your-existing-repo.git
   cd your-existing-repo/backend
   ```

4. **Set up Python and Dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Create the Production `.env` file:**
   ```bash
   nano .env
   ```
   *Paste your real production database URLs here, then save and exit.*

## Step 5: Create the Systemd Service

We need to tell the EC2 server how to keep your backend running 24/7.

1. **Create the service file:**
   ```bash
   sudo nano /etc/systemd/system/hcp-backend.service
   ```

2. **Paste this configuration** (Make sure to replace `your-existing-repo` with your actual repo folder name):
   ```ini
   [Unit]
   Description=Gunicorn instance to serve HCP Engagement Backend
   After=network.target

   [Service]
   User=ec2-user
   Group=ec2-user
   WorkingDirectory=/home/ec2-user/your-existing-repo/backend
   Environment="PATH=/home/ec2-user/your-existing-repo/backend/venv/bin"
   ExecStart=/home/ec2-user/your-existing-repo/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and Start the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hcp-backend
   sudo systemctl start hcp-backend
   ```

> [!IMPORTANT]
> **You are now done!** From now on, whenever you push code changes to the `backend/` folder on your `main` branch, GitHub Actions will securely log into your EC2 server, pull the latest code, and restart the `hcp-backend` service automatically.

## Step 6: Connecting to RDS Database (Later)

When you are ready with your dataset and have created your RDS database, here is exactly how you will add it to the EC2 server:

1. **Get your RDS Credentials:** From AWS RDS, you will need the Endpoint (host), port (usually `5432` for PostgreSQL), username, password, and database name.
2. **SSH into your EC2 server:**
   ```bash
   ssh -i /path/to/your-key.pem ec2-user@<your-ec2-ip>
   ```
3. **Navigate to your backend folder:**
   ```bash
   cd your-existing-repo/backend
   ```
4. **Edit the `.env` file:**
   ```bash
   nano .env
   ```
5. **Add the connection string:** Inside the file, add or update the `DATABASE_URL` variable to point to your new RDS instance. It will look something like this:
   ```env
   DATABASE_URL=postgresql://my_username:my_password@my-rds-database.abcdefg.us-east-1.rds.amazonaws.com:5432/my_database_name
   ```
   *Save the file and exit (in nano, press `Ctrl+O`, `Enter`, then `Ctrl+X`).*
6. **Restart the app to apply the changes:**
   ```bash
   sudo systemctl restart hcp-backend
   ```

That's it! As soon as you run that restart command, your backend will immediately start pulling data from the new RDS database.
