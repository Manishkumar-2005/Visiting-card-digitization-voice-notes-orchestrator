# Visiting Card Digitization & Voice Notes Orchestrator

An end-to-end system for automating the digitization of visiting cards via a Chat UI. This application extracts structured contact data from uploaded card images, checks for duplicate records, updates contact notes using voice recordings, and fires real-time WhatsApp alerts. All process orchestration is driven by a stateful **LangGraph agent**.

---

## Architecture Overview

The system utilizes a modern, decoupled architecture:

```
┌─────────────────┐       HTTP Requests        ┌──────────────────────────────┐
│    React UI     │ <────────────────────────> │      FastAPI Web Server      │
│  (Vite + CSS)   │                            │  (Checkpoints / Static Files)│
└─────────────────┘                            └──────────────┬───────────────┘
                                                              │
                                                              ▼
                                                   ┌─────────────────────┐
                                                   │   LangGraph Agent   │
                                                   │    Orchestration    │
                                                   └──────────┬──────────┘
                                                              │
                    ┌─────────────────┬───────────────────────┼─────────────────────────┐
                    ▼                 ▼                       ▼                         ▼
            ┌──────────────┐   ┌──────────────┐      ┌─────────────────┐       ┌─────────────────┐
            │  Gemini AI   │   │Google Sheets │      │ WhatsApp Cloud  │       │  MongoDB Atlas  │
            │(OCR & Audio) │   │  (Database)  │      │      (API)      │       │ (Chat History)  │
            └──────────────┘   └──────────────┘      └─────────────────┘       └─────────────────┘
```

### 1. Agent Logic (LangGraph)
A stateful graph handles conversation flow. Transitions depend on user inputs and attachments:
- **`extract_card`**: Extracts card details using Gemini Vision OCR.
- **`check_duplicate`**: Queries database/sheets to find existing emails or phone numbers.
- **`save_contact`**: Appends details to Google Sheets and SQLite/MongoDB.
- **`send_notification`**: Triggers manager alerts via WhatsApp.
- **`process_voice`**: Transcribes voice notes using Gemini Audio, extracts amendments using LLM, and updates records.

### 2. Sandbox/Mock Mode
To run without external API accounts, the system automatically falls back to **mock channels**:
- **MongoDB** falls back to a local **SQLite** database.
- **Google Sheets** falls back to a local **mock_google_sheets.json** database.
- **WhatsApp API** logs formatted alert messages to **mock_whatsapp_notifications.log**.
- **Gemini API** yields high-quality pre-seeded mock extractions if no `GEMINI_API_KEY` is provided.

---

## Environment Variables

Create a `.env` file in the `backend/` directory based on `backend/.env.example`:

| Variable | Description | Default / Fallback |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Run environment (`development` or `production`) | `development` |
| `PORT` | Port for FastAPI to listen on | `8000` |
| `GEMINI_API_KEY` | Google Gemini API key (OCR & audio transcription) | *Mock Fallback Mode* |
| `MONGODB_URI` | MongoDB Atlas Connection String | *Local SQLite Database* |
| `GOOGLE_CREDENTIALS_JSON` | Raw Google Service Account credentials JSON string | *Local mock_google_sheets.json* |
| `GOOGLE_SHEET_NAME` | Name of the spreadsheet in Google Drive | `Visiting Cards Orchestrator` |
| `WHATSAPP_TOKEN` | WhatsApp Cloud API Access Token | *Local mock_whatsapp_notifications.log* |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business Phone Number ID | *None* |
| `WHATSAPP_RECIPIENT_PHONE` | Manager phone number to receive alerts | *None* |

---

## How to Run Locally

### Method A: Docker Compose (Recommended)
This runs the complete stack (both frontend and backend) inside containerized environments:

1. Place your configuration keys inside `backend/.env`.
2. Run command at root:
   ```bash
   docker-compose up --build
   ```
3. Open your browser to `http://localhost`. (FastAPI backend will run at `http://localhost:8000`).

---

### Method B: Manual / Native Local Run

#### 1. Start the Backend API
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server:
   ```bash
   python -m app.main
   ```
   *The backend will boot up on `http://localhost:8000`.*

#### 2. Start the Frontend Dev Server
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   *The UI will start on `http://localhost:5173`.*

---

## Step-by-Step Render Deployment Guide

Render is an excellent platform for deploying this stack. The backend is deployed as a Docker Web Service, and the React frontend is deployed as a Static Site.

### Step 1: Deploy Backend on Render (Web Service)
1. Log in to [Render](https://render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository containing the codebase.
4. Set the following configurations:
   - **Name**: `visiting-card-backend`
   - **Root Directory**: `backend` (Critical: point this to the backend directory)
   - **Language**: `Docker` (Render will automatically detect the `Dockerfile` inside the backend directory)
   - **Instance Type**: `Free`
5. Click **Advanced** and add the following **Environment Variables**:
   - `PORT`: `10000` (or leave default, Render sets this automatically)
   - `ENVIRONMENT`: `production`
   - `GEMINI_API_KEY`: *Your Gemini API Key*
   - `MONGODB_URI`: *Your MongoDB Connection String*
   - `GOOGLE_CREDENTIALS_JSON`: *Your raw Service Account JSON*
   - `WHATSAPP_TOKEN`: *Your WhatsApp API Token*
   - `WHATSAPP_PHONE_NUMBER_ID`: *Your WhatsApp ID*
   - `WHATSAPP_RECIPIENT_PHONE`: *Your Manager phone number*
6. Click **Deploy Web Service**.
7. Once successfully deployed, copy the generated Web Service URL (e.g., `https://visiting-card-backend.onrender.com`).

---

### Step 2: Deploy Frontend on Render (Static Site)
1. On the Render dashboard, click **New +** and select **Static Site**.
2. Connect your GitHub repository.
3. Set the following configurations:
   - **Name**: `visiting-card-frontend`
   - **Root Directory**: `frontend` (Critical: point this to the frontend directory)
   - **Build Command**: `npm run build`
   - **Publish Directory**: `dist`
4. Click **Advanced** and add the following **Environment Variable**:
   - `VITE_BACKEND_URL`: `https://visiting-card-backend.onrender.com` (Use the URL of your backend deployed in Step 1)
5. Click **Create Static Site**.
6. Render will compile your React app using Vite and host it statically for free. Open the static site link (e.g., `https://visiting-card-frontend.onrender.com`) to use the application!
