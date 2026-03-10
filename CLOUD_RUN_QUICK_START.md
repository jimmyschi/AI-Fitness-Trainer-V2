# Cloud Run Quick Start

This guide walks you through deploying the Fitness App to Cloud Run in just a few steps.

---

## Prerequisites

1. GitHub repository is set up
2. You've read the full `CLOUD_RUN_SETUP.md` guide
3. GCP APIs are enabled (Cloud Run API, Cloud Build API, Container Registry API)

---

## Step 1: Create GCP Service Account & Get Key

Follow **Steps 1-3 in CLOUD_RUN_SETUP.md**:
- Create `github-actions-sa` service account
- Grant required roles
- Download the JSON key file

---

## Step 2: Add GitHub Secrets

1. Go to GitHub repository → **Settings → Secrets and variables → Actions**
2. Add two secrets:
   - `GCP_SA_KEY`: (paste entire JSON key file contents)
   - `GCP_PROJECT_ID`: `gleaming-bus-449020-t9`

---

## Step 3: Update Frontend Backend URL

Before deploying, update the frontend to know where the backend is.

1. Edit `fitness-frontend/.env`:
```
REACT_APP_API_URL=https://fitness-backend-xxxxx-uc.a.run.app
```

**Note:** Replace `fitness-backend-xxxxx-uc.a.run.app` with your actual backend Cloud Run URL. If this is your first deployment:
- Deploy anyway; GitHub Actions will show the URLs in the logs
- Then update this file with the actual backend URL and push again

---

## Step 4: Push to GitHub

```bash
git add .
git commit -m "Enable Cloud Run deployment"
git push origin main
```

This triggers the GitHub Actions workflow which will:
1. Build Django image → push to GCR
2. Deploy Django to Cloud Run
3. Build React image → push to GCR
4. Deploy React to Cloud Run
5. Show deployment URLs in the workflow summary

---

## Step 5: Monitor Deployment

1. Go to GitHub repository → **Actions** tab
2. Watch the workflow run
3. When complete, check the **Summary** section for deployed URLs

---

## Getting Cloud Run URLs

After deployment, get the service URLs:

```bash
gcloud run services list --region=us-central1
```

Or view in **GCP Console → Cloud Run**

---

## Environment Variables for Django

The workflow deploys Django with default settings. If you need custom environment variables:

1. Edit `.github/workflows/build-push-deploy-cloud-run.yml`
2. Add `--set-env-vars` flags to the `gcloud run deploy` command:
```yaml
--set-env-vars "DATABASE_URL=...,GCS_BUCKET_NAME=..."
```

---

## Logs & Debugging

View Cloud Run logs:

```bash
# Backend logs
gcloud run services logs read fitness-backend --region=us-central1 --limit=50

# Frontend logs
gcloud run services logs read fitness-frontend --region=us-central1 --limit=50
```

Or in **GCP Console → Cloud Run → Click service → Logs** tab

---

## Stopping Services

To stop billing:

```bash
# Delete backend service
gcloud run services delete fitness-backend --region=us-central1

# Delete frontend service
gcloud run services delete fitness-frontend --region=us-central1
```

---

## Cost

- First 180k vCPU-seconds/month free (backend)
- First 360k GB-seconds/month free (memory)
- First 2M requests/month free
- **Expected cost for light usage:** $0–5/month (likely free)

Check usage in **GCP Console → Billing → SKUs** or **Cloud Run dashboard**

---

## Next Steps

1. ✅ Follow CLOUD_RUN_SETUP.md to set up GCP auth
2. ✅ Add GitHub Secrets
3. ✅ Update `fitness-frontend/.env` with backend URL
4. ✅ Push to GitHub and watch deployment
5. ✅ Share the Cloud Run URLs with recruiters!

---

## Troubleshooting

**Q: Deployment fails with "permission denied"**
- Ensure service account has all required roles (see CLOUD_RUN_SETUP.md Step 2)
- Re-download and re-upload the JSON key to GitHub

**Q: Frontend shows blank page or 404**
- Check that `REACT_APP_API_URL` is set correctly in `fitness-frontend/.env`
- Verify backend is responding: visit the Django Cloud Run URL in browser (should show Django admin or API docs)

**Q: Backend returns 5xx errors**
- Check logs: `gcloud run services logs read fitness-backend --limit=100`
- Verify environment variables are set (DATABASE_URL, GCS_BUCKET_NAME, etc.)
- Ensure GCS bucket exists and service account can access it

**Q: High costs appearing**
- Check **GCP Console → Cloud Run** to see CPU/memory usage
- Reduce `--memory` or `--max-instances` in the workflow if needed
- Cloud Run only charges for actual usage, so idle services are free
