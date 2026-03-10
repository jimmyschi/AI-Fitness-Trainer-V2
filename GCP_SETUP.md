# GCP Service Account Setup for GitHub Actions

## Step 1: Create Service Account in GCP

1. Go to [GCP Console](https://console.cloud.google.com)
2. Select your project: `gleaming-bus-449020-t9`
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
   - Name: `github-actions-sa`
   - Description: "GitHub Actions for CI/CD"
   - Click **Create and Continue**

5. Grant Roles to the service account:
   - Add roles:
     - **Container Registry Service Agent** (for pushing to GCR)
     - **Kubernetes Engine Developer** (for GKE deployments)
   - Click **Continue** and then **Done**

## Step 2: Create and Download Key

1. In the Service Accounts list, click the newly created `github-actions-sa`
2. Go to the **Keys** tab
3. Click **Add Key** → **Create new key**
4. Choose **JSON** format
5. Click **Create** — this downloads a JSON file (save it securely)

## Step 3: Add to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:
   - **Name:** `GCP_SA_KEY`
   - **Value:** Paste the entire contents of the downloaded JSON file
4. Click **Add secret**

## Step 4: Get GKE Cluster Info

Also add these GitHub Secrets:
- **Name:** `GKE_CLUSTER_NAME`
  **Value:** (ask/check in GCP Console under Kubernetes Engine → Clusters) — typically something like `fitness-cluster`
  
- **Name:** `GKE_ZONE`
  **Value:** The zone of your cluster (e.g., `us-central1-a`)

- **Name:** `GCP_PROJECT_ID`
  **Value:** `gleaming-bus-449020-t9`

Done! GitHub Actions can now authenticate with GCP.
