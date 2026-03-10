 # Cloud Run Deployment Setup

This guide explains how to set up Cloud Run deployment for the Fitness App backend and frontend using GitHub Actions.

## Architecture

- **Backend (Django):** Cloud Run service with Cloud Storage (GCS) integration
- **Frontend (React):** Cloud Run service serving static assets
- **Container Registry:** Google Container Registry (GCR) in your GCP project
- **CI/CD:** GitHub Actions workflow that builds, pushes, and deploys automatically

---

## Step 1: Enable Required GCP APIs

1. Go to [GCP Console → APIs & Services](https://console.cloud.google.com/apis/dashboard)
2. Click **+ ENABLE APIS AND SERVICES**
3. Search for and enable these APIs:
   - **Cloud Run API**
   - **Cloud Build API**
   - **Container Registry API** (should already be enabled)

---

## Step 2: Create Service Account for GitHub Actions

1. Go to [GCP Console → IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **+ CREATE SERVICE ACCOUNT**
3. Fill in:
   - **Service Account ID:** `github-actions-sa`
   - **Display Name:** GitHub Actions Service Account
4. Click **CREATE AND CONTINUE**
5. Grant these roles:
   - **Service Account User**
   - **Cloud Run Admin**
   - **Container Registry Service Agent**
   - **Cloud Build Service Account**
   - **Storage Admin** (for GCS access)
6. Click **CONTINUE** then **DONE**

---

## Step 3: Create and Download Service Account Key

1. In [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts), click on `github-actions-sa`
2. Go to **KEYS** tab
3. Click **ADD KEY → Create new key**
4. Choose **JSON** and click **CREATE**
5. This downloads a `github-actions-sa-*.json` file — **keep this safe**

---

## Step 4: Add GitHub Secrets

1. Go to your GitHub repository → **Settings → Secrets and variables → Actions**
2. Click **New repository secret** and add:

| Secret Name | Value |
|-------------|-------|
| `GCP_SA_KEY` | (paste entire contents of the JSON key file from Step 3) |
| `GCP_PROJECT_ID` | `gleaming-bus-449020-t9` |

---

## Step 5: That's It! GitHub Actions Handles the Rest

✅ **You're done with manual setup!** The GitHub Actions workflow (`.github/workflows/build-push-deploy-cloud-run.yml`) will automatically:
- Build both Django and React Docker images
- Push to GCR
- Deploy to Cloud Run

Just push your code to GitHub, and the workflow runs automatically.

---

## (Optional) Manual Deployment

If you want to deploy manually instead of using GitHub Actions:

### Authenticate with GCP

```bash
# Save the JSON key file locally (keep it safe!)
# Then authenticate gcloud
gcloud auth activate-service-account --key-file=/path/to/github-actions-sa-*.json
gcloud config set project gleaming-bus-449020-t9
```

### Build and Push Django Image

```bash
docker build -f fitness_backend/Dockerfile.django \
  -t gcr.io/gleaming-bus-449020-t9/django-app:latest \
  .

docker push gcr.io/gleaming-bus-449020-t9/django-app:latest
```

### Deploy Django to Cloud Run

```bash
gcloud run deploy fitness-backend \
  --image=gcr.io/gleaming-bus-449020-t9/django-app:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=2Gi \
  --timeout=3600 \
  --port 8000
```

### Build and Push React Image

```bash
docker build -f fitness-frontend/Dockerfile.frontend \
  -t gcr.io/gleaming-bus-449020-t9/react-app:latest \
  fitness-frontend/

docker push gcr.io/gleaming-bus-449020-t9/react-app:latest
```

### Deploy React to Cloud Run

```bash
gcloud run deploy fitness-frontend \
  --image=gcr.io/gleaming-bus-449020-t9/react-app:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=512Mi \
  --port 80
```

### Get Cloud Run URLs

After deployment, get the service URLs:

```bash
gcloud run services list --region=us-central1
```

The backend and frontend will have URLs like:
- Backend: `https://fitness-backend-xxxxx-uc.a.run.app`
- Frontend: `https://fitness-frontend-xxxxx-uc.a.run.app`

---

## Step 6: Update Frontend Environment Variables (If Manual Deployment)

Once you have the backend Cloud Run URL, update `fitness-frontend/.env`:

```
REACT_APP_API_URL=https://fitness-backend-xxxxx-uc.a.run.app
```

Then rebuild and redeploy the frontend.

---

## Cost Estimate

- **Compute (on-demand):** ~$0.00002400/vCPU-second, billed to nearest 100ms (first 180k vCPU-seconds free per month)
- **Memory:** ~$0.00000250/GB-second (first 360k GB-seconds free per month)
- **Requests:** First 2M requests/month free, then $0.40 per million

**Expected cost for light usage:** ~$0–5/month (often covered by free tier)

---

## Monitoring and Logs

View logs for your Cloud Run services:

```bash
# Backend logs
gcloud run services describe fitness-backend --region=us-central1

# View real-time logs
gcloud run services logs read fitness-backend --region=us-central1 --limit=50
```

---

## GitHub Actions Workflow (Recommended)

The automated workflow (`.github/workflows/build-push-deploy-cloud-run.yml`) will:
1. Trigger on push to `main` or `develop` branch
2. Build Django and React images
3. Push to GCR
4. Deploy both services to Cloud Run
5. Output the Cloud Run service URLs

No manual deployment needed—just push to GitHub and the workflow runs automatically!
