# Talent Ranker

**AI-powered resume screening for HR teams — no technical setup required.**

Talent Ranker is a local web application that reads multiple resumes, evaluates each candidate against your job description, and returns an objective ranked list with clear justifications. Upload files, click one button, and get results. All recruiter AI rules are built in — your team never writes prompts or configures an AI system.

---

## Who this is for

- HR recruiters screening a batch of applicants
- Hiring managers comparing finalists for a role
- Small teams without access to an ATS with built-in AI scoring

You need basic computer skills (uploading files, using a web browser) and one OpenAI API key. No coding, no prompt engineering, no cloud deployment.

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-resume upload** | Drag and drop PDF, Word (.docx), or plain text files — including scanned PDFs |
| **Job-description matching** | Paste a role description for targeted scoring, or leave blank for general evaluation |
| **Ranked output** | Numbered list from most to least qualified, with justification for top candidates |
| **Follow-up chat** | Ask for candidate summaries, interview recommendations, or skill-gap analysis |
| **Built-in AI persona** | Senior HR recruiter rules, unbiased screening, and BRIEF-format summaries — all preconfigured |
| **One-time setup** | Enter your API key once in the Settings screen |

---

## Quick start

### Requirements

- **Python 3.9 or newer** ([download](https://www.python.org/downloads/))
- **An OpenAI API key** ([get one here](https://platform.openai.com/api-keys))

### Start the app

Open a terminal, navigate to the project folder, and run:

```bash
cd talent-ranker
chmod +x start.sh
./start.sh
```

The script will:

1. Create a Python environment (first run only)
2. Install dependencies (first run only)
3. Start the web server at `http://localhost:8000`
4. Open your browser automatically (macOS)

To stop the app, press **Ctrl+C** in the terminal.

### First-time setup (30 seconds)

1. Your browser opens to the Talent Ranker home page
2. Click **Settings** (gear icon, top right)
3. Paste your OpenAI API key and click **Save**
4. Upload resumes and click **Rank Candidates**

That is the entire setup. The API key is saved locally and reused on every launch.

---

## How to use

### Step 1 — Upload resumes

- Drag files onto the upload area, or click to browse
- Supported formats: **PDF**, **DOCX**, **TXT**
- PDFs are read with multiple extractors; scanned/image PDFs use AI vision OCR when an API key is configured
- Add as many candidates as you need in one batch

### Step 2 — Add a job description (optional)

Paste the role requirements into the text box. The AI uses this to score fit. If you leave it blank, candidates are evaluated against general professional standards.

### Step 3 — Rank candidates

Click **Rank Candidates**. The AI will:

1. Read every resume
2. Extract experience, skills, education, and achievements
3. Score each candidate (0–100 fit)
4. Return a numbered ranking with justification for the top picks

### Step 4 — Ask follow-up questions

After ranking, use the chat panel to dig deeper. Example prompts:

- *"Give me a summary of the top-ranked candidate."*
- *"Who would you recommend for a first-round interview?"*
- *"What are the key skill gaps for the lowest-ranked candidate?"*

Quick-action chips are provided for common questions.

---

## Example output

```
1. Jane Martinez – 9 years of B2B marketing leadership with measurable campaign ROI.
2. David Chen – Strong digital skills but limited team-management experience.
3. Priya Nair – Early-career profile with relevant certifications, fewer quantified results.

Jane Martinez leads the ranking based on depth and recency of relevant experience…
```

When you request a candidate summary, the response follows a **BRIEF** structure:

- **Background** — career context from the resume
- **Reason** — why the candidate matters for the role
- **Information** — key facts and achievements
- **End/Expected Outcome** — likely fit or contribution
- **Follow-Up** — one validation question or next step

---

## How the AI works

Talent Ranker embeds a senior HR Talent Recruiter persona that:

- Bases every judgment **only** on explicit resume and job-description content
- Never invents details or makes unsupported assumptions
- Ignores protected characteristics (age, gender, ethnicity, etc.)
- Prioritizes experience depth, recency, quantifiable achievements, skill alignment, education, and career progression
- Keeps responses under 400 words unless you ask for deeper analysis
- Treats all candidate data as confidential

You interact entirely through the web UI. The system prompt, ranking rules, and response format are handled automatically in `app/prompts.py`.

---

## Configuration

| Setting | How to set | Default |
|---------|------------|---------|
| OpenAI API key | **Settings** in the app, or `.env` file | — |
| AI model | **Settings** in the app, or `OPENAI_MODEL` in `.env` | `gpt-4o-mini` |
| Server port | `PORT` environment variable | `8000` |

### Using a `.env` file (optional)

If you prefer editing a file instead of the Settings screen:

```bash
cp .env.example .env
```

Then open `.env` and set your values:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

### Running on a different port

```bash
PORT=3000 ./start.sh
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"Setup required" banner** | Open Settings and paste a valid OpenAI API key |
| **"Could not read text from file"** | Ensure the PDF is not corrupted. Scanned PDFs need an OpenAI API key in Settings for automatic OCR |
| **"Unsupported file"** | Use PDF, DOCX, or TXT only |
| **Browser doesn't open** | Manually visit `http://localhost:8000` |
| **`python3: command not found`** | Install Python 3.9+ from [python.org](https://www.python.org/downloads/) |
| **Port already in use** | Run `PORT=8001 ./start.sh` or stop the other process using port 8000 |
| **Analysis or chat error** | Check that your API key is valid and has available credits at [platform.openai.com](https://platform.openai.com) |

---

## Privacy and data handling

- Resumes are saved locally in the `uploads/` folder during analysis
- Resume text is sent to **OpenAI** for AI processing — review [OpenAI's data policies](https://openai.com/policies) for your compliance requirements
- Chat sessions are stored in server memory and cleared when the server restarts
- The API key is stored in a local `.env` file on your machine

For sensitive hiring data, run the app on a trusted machine and ensure your organization's policies permit use of third-party AI APIs.

---

## Project structure

```
talent-ranker/
├── start.sh              # One-command launcher
├── requirements.txt      # Python dependencies
├── .env.example          # API key template
├── README.md
├── app/
│   ├── main.py           # Web server and API routes
│   ├── ai_service.py     # OpenAI integration
│   ├── prompts.py        # Embedded recruiter AI rules
│   ├── resume_parser.py  # PDF / DOCX / TXT text extraction
│   └── static/
│       ├── index.html    # Web UI
│       ├── styles.css
│       └── app.js
└── uploads/              # Local resume storage (temporary)
```

---

## License

This project is provided as-is for internal hiring workflows. Adapt and extend as needed for your organization.