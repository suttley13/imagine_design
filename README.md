# REDESIGN AI PRO

An AI-powered room redesign application that transforms your space with personalized design recommendations.

## Features

- Upload a photo of your room and an inspiration image
- Get AI-powered redesign suggestions
- Generate visual transformations of your space
- Download high-quality redesigned room images
- Copy design descriptions to your clipboard

## CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment to Google Cloud Run:

1. **Workflow Trigger**: Automatically triggered on pushes to the `main` branch
2. **Build Process**: Builds a Docker container image
3. **Deployment**: Automatically deploys to Google Cloud Run
4. **Configuration**: The workflow is defined in `.github/workflows/deploy.yml`

### Setting Up GCP Authentication

To enable the GitHub Actions workflow to deploy to Google Cloud Run, you need to:

1. Create a Service Account in Google Cloud with the following roles:
   - Cloud Run Admin
   - Storage Admin
   - Service Account User

2. Create a JSON key for this Service Account

3. Add the key as a GitHub Secret:
   - Go to your GitHub repository 
   - Navigate to Settings → Secrets and variables → Actions
   - Create a new repository secret named `GCP_SA_KEY`
   - Paste the entire JSON content of your service account key file

## Development Workflow

1. Clone the repository
2. Make your changes locally
3. Commit and push to GitHub
4. GitHub Actions will automatically build and deploy to Cloud Run
5. Visit the live site at: https://redesignai.pro

## Rollback Process

If you need to roll back to a previous version:

1. In Google Cloud Console, go to Cloud Run → Services → imagine-design
2. Click the "REVISIONS" tab
3. Find the revision you want to roll back to
4. Use the menu (three dots) to select "Direct 100% of traffic"

Alternatively, you can use Git to revert commits and push them to GitHub to trigger a deployment of the previous version.

## Setup

1. Clone the repository:
```bash
git clone [your-repo-url]
cd [repo-name]
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the root directory with:
```
CLAUDE_API_KEY=your_claude_api_key
GEMINI_API_KEY=your_gemini_api_key
```

4. Run the application locally:
```bash
python app.py
```

## Deployment to Google Cloud Run

1. Install Google Cloud CLI and initialize:
```bash
gcloud init
```

2. Build and deploy:
```bash
gcloud builds submit --tag gcr.io/[PROJECT_ID]/ai-room-redesign
gcloud run deploy ai-room-redesign --image gcr.io/[PROJECT_ID]/ai-room-redesign --platform managed
```

3. Set environment variables in Google Cloud Run:
- Go to Google Cloud Console
- Navigate to Cloud Run
- Select your service
- Add environment variables for CLAUDE_API_KEY and GEMINI_API_KEY

## Usage

1. Upload a photo of your current room
2. Upload an inspiration room photo
3. Click "Imagine Design" to get redesign suggestions
4. Click on suggestion numbers to view different redesigns
5. Use the comparison feature to see before/after views

## Technologies Used

- Flask (Python web framework)
- Anthropic Claude API (for redesign suggestions)
- Google Gemini API (for image generation)
- HTML/CSS/JavaScript (frontend)
- Google Cloud Run (hosting) 