# Deployment Guide

This document outlines practical ways to deploy the Content Production Team application to production.

## Recommended deployment path

For most teams, the easiest production path is:

1. Deploy the Streamlit app as a containerized service.
2. Store the OpenAI API key in the platform's secret management feature.
3. Configure the app to run on port 8501.
4. Enable HTTPS and authentication if the app will be shared outside your organization.

## Deployment options

### 1. Streamlit Community Cloud

Best for: simple demos, MVPs, and quick public sharing.

Steps:

1. Push the repository to GitHub.
2. Open Streamlit Community Cloud.
3. Create a new app from the repository.
4. Set the environment variable OPENAI_API_KEY in the app settings.
5. Launch the deployment.

Notes:

- This is the fastest option.
- It works well if you want the simplest path without managing servers.

### 2. Render

Best for: a simple managed web service.

Steps:

1. Create a Render account.
2. Create a new web service from the repository.
3. Use the Dockerfile for the build.
4. Set the port to 8501.
5. Add the OPENAI_API_KEY secret.
6. Deploy.

### 3. Railway

Best for: fast deployment with straightforward environment variables.

Steps:

1. Connect the GitHub repository to Railway.
2. Create a new service from the repository.
3. Choose the Docker deployment path.
4. Add the OPENAI_API_KEY secret.
5. Deploy.

### 4. Fly.io

Best for: container-first deployments with global regions.

Steps:

1. Install the Fly CLI.
2. Run `fly launch` from the project root.
3. Add `OPENAI_API_KEY` as a secret using `fly secrets set`.
4. Deploy with `fly deploy`.

### 5. Azure App Service

Best for: teams already using Microsoft Azure.

Steps:

1. Create an Azure Web App.
2. Configure the runtime as Python.
3. Set startup commands for Streamlit.
4. Add the OpenAI API key in the app settings.
5. Deploy the code or a container image.

### 6. AWS App Runner

Best for: AWS-native deployments.

Steps:

1. Create an App Runner service from a container image.
2. Configure port 8501.
3. Add the OPENAI_API_KEY secret.
4. Deploy.

## Environment variables

The app expects the following values:

- OPENAI_API_KEY: required for live LLM calls
- OPENAI_MODEL: defaults to gpt-4o
- CONTENT_MIN_SCORE: defaults to 70
- CONTENT_MAX_ATTEMPTS: defaults to 3

## Container notes

The repository includes a Dockerfile that exposes port 8501 and starts Streamlit with:

```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

## Security checklist

Before going live:

- move secrets to the platform secret store
- set up HTTPS if the service is public
- add authentication if necessary
- set resource limits and monitor OpenAI usage
- rotate secrets periodically

## Suggested production improvements

- add persistence for workflow outputs
- add user authentication
- add logging and error tracking
- add rate limiting and cost controls
- add a database for history and audit trails
