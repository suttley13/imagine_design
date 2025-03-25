# AI Room Redesign App

This application uses AI to help users redesign their rooms by providing suggestions based on inspiration images and generating visualizations of the suggested changes.

## Features

- Upload current room and inspiration room images
- Get AI-powered redesign suggestions from Claude
- Generate visual representations of the suggestions using Gemini
- Interactive UI to view and compare different redesign options

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