# Visiting Card Digitization & Voice Notes Orchestrator

An end-to-end agentic application for automating the digitization of physical visiting cards and augmenting them with voice notes. Built with a **React (Vite) frontend** and a **FastAPI backend**, the entire flow is orchestrated using a stateful **LangGraph agent** powered by the **Gemini 3.5 Flash** model.

---

## Architectural Approach

Our solution utilizes a decoupled client-server architecture with an agentic state-machine at its core:

```
┌─────────────────┐       HTTP Requests        ┌──────────────────────────────┐
│  React Vite UI  │ <────────────────────────> │      FastAPI Web Server      │
│  (Modern CSS)   │                            │   (SQLite / MongoDB Atlas)   │
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

### 1. State Machine Orchestration (LangGraph)
We model the card digitization flow as a directed state graph. The state persists user messages, card structures, duplicate contact states, and action requirements:
*   **Card Extraction**: Uploaded card images are processed by Gemini Vision to extract structured JSON (name, company, email, phone, etc.).
*   **Human-In-The-Loop Approval**: Extracted data is presented to the user on the frontend to modify and approve.
*   **Duplicate Detection**: Before saving, the database (SQLite/MongoDB) and Google Sheet are queried. If a duplicate is found (matching email/phone), the agent prompts the user to either merge or create a new entry.
*   **Sync & Alerts**: Once approved, the contact is saved to Google Sheets and SQLite/MongoDB, and a real-time notification alert is dispatched via WhatsApp.
*   **Voice Amendment Node**: Users can record voice notes (e.g. "He changed his role to Lead Developer"). Gemini Audio transcribes the voice, extracts the amendments, and patches the database & Google Sheet records in real-time.

### 2. Dual Database Architecture
*   **SQLite Fallback**: Excellent for zero-config local testing and lightweight deployments.
*   **MongoDB Atlas Integration**: Automatically replaces SQLite for persistent production servers when a `MONGODB_URI` is provided.

### 3. Graceful Mock/Sandbox Modes
If API keys or Google Service Accounts are omitted, the system falls back to sandboxed mock handlers:
*   Generates mock card extractions from predefined templates.
*   Logs WhatsApp notifications locally to a file.
*   Uses a local JSON database fallback for Google Sheets.

---

## 🛠️ Setup Instructions (Local Development)

### Prerequisites
*   Node.js (v18+)
*   Python 3.10+
*   Git

### 1. Environment Configuration
Create a `.env` file inside the `backend/` directory. You can base it on `backend/.env.example`.

```env
ENVIRONMENT=development
PORT=8000

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Databases (Leave MONGODB_URI empty to use SQLite automatically)
MONGODB_URI=
GOOGLE_SHEET_NAME=Visitor_cards_data
GOOGLE_CREDENTIALS_JSON={"type": "service_account", ...}

# WhatsApp Notification Credentials (Optional, falls back to local log)
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_RECIPIENT_PHONE=
```

---

### 2. Running Locally (Method A: Manual Setup)

#### Start the Backend API
1. Navigate to the `backend` directory:
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
4. Run the development server:
   ```bash
   python -m app.main
   ```
   *The API will boot on `http://localhost:8000`*

#### Start the Frontend Web App
1. Open a new terminal and navigate to `frontend`:
   ```bash
   cd frontend
   ```
2. Install npm modules:
   ```bash
   npm install
   ```
3. Launch Vite development server:
   ```bash
   npm run dev
   ```
   *The UI will start on `http://localhost:5173`*

---

### 3. Running Locally (Method B: Docker Compose)
If you have Docker installed, you can spin up the entire frontend and backend with a single command:
```bash
docker-compose up --build
```
Open your browser to `http://localhost` (Frontend on port `80`, Backend API on port `8000`).

---

## 🚀 Production Deployment Options

### Option A: Render (SQLite / Ephemeral Setup) - Free Tier
Perfect for demo hosting.
1. **Backend Web Service**:
   *   Create a Web Service on Render pointing to your repository.
   *   Set **Root Directory** to `backend` and **Language** to `Docker`.
   *   Configure environment variables. Leave `MONGODB_URI` blank to fallback to SQLite.
2. **Frontend Static Site**:
   *   Create a Static Site on Render pointing to your repository.
   *   Set **Root Directory** to `frontend`.
   *   Build Command: `npm run build`
   *   Publish Directory: `dist`
   *   Set Environment Variable `VITE_BACKEND_URL` to your Render backend web service URL.

> [!WARNING]
> Render's free tier has ephemeral disks. Every time the backend container restarts (due to inactivity or redeploys), local SQLite chat history will be cleared. However, your digitized contact records are **completely safe** because they are mirrored live onto Google Sheets!

### Option B: Render with Persistent Disk (SQLite Production)
If you want persistent SQLite history on Render:
1. Complete **Option A** to deploy the Backend.
2. Go to the Backend dashboard, click **Disks** > **Add Disk**.
3. Set **Mount Path** to `/app/data` (Size: 1 GB minimum, costs ~$1/mo). This ensures SQLite and uploads are preserved.

### Option C: MongoDB Atlas Cloud + Render Free Tier (100% Free Persistent Setup)
1. Sign up for a free sandbox tier cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Grab your connection string and add it to `MONGODB_URI` in your Render Environment Variables.
3. Chat history and states will now be stored in the cloud. You get persistent databases and hosting for free without paying for a disk.
