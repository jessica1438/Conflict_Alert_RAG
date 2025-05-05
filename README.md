# Conflict_Alert_RAG
This Streamlit app uploads CSVs, extracts facts, detects conflicts with regex + NLP, and answers queries using a RAG system with LangChain + GPT-4. It’s Dockerized, deployed via AWS ECR. Working on deploying this in ECS Fargate, and automate with GitHub Actions for production.

Features: 

1) Upload multiple CSV files as document sources
   
2) Extract facts using regex + spaCy NLP

3) Maintain a knowledge base + conflict log
   
4) Retrieve answers using LangChain RAG pipeline with FAISS

5) Explain conflicts using a GPT-4 agent
  
6) Dockerized for reproducible builds
   
7) Deployed to AWS ECS Fargate via Terraform
    
8) CI/CD automation using GitHub Actions

🏗 Project Setup

1️⃣ Local Run (For Testing)

Clone this repository:
```
git clone <repo_url>
cd rag-conflict-app
```
Install dependencies:
```
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```
Store your OpenAI key in a .env file:
```
OPENAI_API_KEY=your_openai_api_key_here
```
Run the app locally:
```
streamlit run app.py
```
2️⃣ Docker Build & Run

Build the Docker image:
```
docker build -t rag-conflict-app .
```
Run the container:
```
docker run -p 8501:8501 --env-file .env rag-conflict-app
```
3️⃣ Push to AWS ECR

Authenticate Docker:
```
aws ecr get-login-password --region us-east-1 | \
docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com
```
Tag + push the image:
```
docker tag rag-conflict-app:latest <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/rag-conflict-app:latest
docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/rag-conflict-app:latest
```
4️⃣ Deploy with Terraform

Set up your terraform-deploy/ folder with main.tf, variables.tf, outputs.tf, terraform.tfvars.

Initialize + apply:
```
terraform init
terraform apply
```
Terraform will provision ECS Fargate + ALB + Security Groups and deploy the app.

🛣 Future Roadmap

✅ Current: Basic conflict detection + RAG answering + cloud deployment🔜 Next:

Add real-time monitoring + logging (CloudWatch)

Integrate unit + integration tests for CI/CD pipeline

Add user authentication + role-based access

Improve vector search with hybrid (text + metadata) retrieval

Scale ECS service with autoscaling policies

Add frontend polish + multi-language support
