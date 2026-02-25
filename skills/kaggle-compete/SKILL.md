# Skill: kaggle-compete

## Purpose
A comprehensive toolkit for interacting with Kaggle competitions: uploading notebooks, submitting predictions, downloading data, checking status, and viewing leaderboards.

## Required Environment Variables

In workspace `.env`:
- `KAGGLE_USERNAME` — your Kaggle username
- `KAGGLE_KEY` — your Kaggle API key (supports both KGAT tokens and legacy API keys)

## Scripts

### 1. `run.sh` — Upload a notebook to a competition
Upload a Kaggle notebook to a competition as a private kernel with GPU enabled.

```bash
./skills/kaggle-compete/run.sh <competition_url> --notebook <path_to_notebook.ipynb>
```

**Example:**
```bash
./skills/kaggle-compete/run.sh "https://www.kaggle.com/competitions/titanic" --notebook temp/solution.ipynb
```

| Parameter | Required | Description |
|---|---|---|
| `<competition_url>` | Yes | URL like `https://www.kaggle.com/competitions/{slug}` |
| `--notebook <path>` | Yes | Path to a `.ipynb` notebook file |

---

### 2. `list-competitions.sh` — List available competitions
Search and browse Kaggle competitions with filtering and sorting.

```bash
./skills/kaggle-compete/list-competitions.sh [--search <query>] [--category <cat>] [--sort <sort>] [--json]
```

**Examples:**
```bash
# Search for NLP competitions
./skills/kaggle-compete/list-competitions.sh --search "nlp"

# List featured competitions as JSON
./skills/kaggle-compete/list-competitions.sh --category featured --json

# Sort by deadline
./skills/kaggle-compete/list-competitions.sh --sort earliestDeadline
```

| Parameter | Required | Description |
|---|---|---|
| `--search <query>` | No | Search by keyword |
| `--category <cat>` | No | Filter: featured, research, playground, getting-started, masters, community |
| `--sort <sort>` | No | Sort: grouped, prize, earliestDeadline, latestDeadline, numberOfTeams, recentlyCreated |
| `--page <n>` | No | Page number (default: 1) |
| `--page-size <n>` | No | Results per page (default: 20) |
| `--json` | No | Output as JSON |

---

### 3. `download-dataset.sh` — Download competition or dataset files
Download data files from competitions or public datasets.

```bash
./skills/kaggle-compete/download-dataset.sh <target> [--output <dir>] [--file <name>] [--list]
```

**Examples:**
```bash
# Download competition data
./skills/kaggle-compete/download-dataset.sh titanic --output ./data/

# Download a public dataset
./skills/kaggle-compete/download-dataset.sh zillow/zecon --output ./data/

# List files without downloading
./skills/kaggle-compete/download-dataset.sh titanic --list

# Download from URL
./skills/kaggle-compete/download-dataset.sh "https://www.kaggle.com/competitions/titanic" --output ./data/
```

| Parameter | Required | Description |
|---|---|---|
| `<target>` | Yes | Competition slug/URL or dataset ref (`owner/slug`) |
| `--output <dir>` | No | Download directory (default: current dir) |
| `--file <name>` | No | Download specific file only |
| `--list` | No | List available files without downloading |

---

### 4. `submit.sh` — Submit predictions to a competition
Upload a submission file and check the score.

```bash
./skills/kaggle-compete/submit.sh <competition> --file <submission.csv> [--message <msg>]
```

**Examples:**
```bash
# Submit predictions
./skills/kaggle-compete/submit.sh titanic --file submission.csv --message "XGBoost v2"

# Submit from URL
./skills/kaggle-compete/submit.sh "https://www.kaggle.com/competitions/titanic" --file output.csv
```

| Parameter | Required | Description |
|---|---|---|
| `<competition>` | Yes | Competition URL or slug |
| `--file <path>` | Yes | Path to submission file |
| `--message <msg>` | No | Submission description |

**Output:** Shows submission status and public score (if available immediately).

---

### 5. `check-status.sh` — Check notebook execution status
Monitor a running kernel and optionally poll until completion.

```bash
./skills/kaggle-compete/check-status.sh <kernel_ref> [--poll] [--logs] [--interval <sec>]
```

**Examples:**
```bash
# Check status once
./skills/kaggle-compete/check-status.sh username/my-notebook

# Poll until complete, show logs
./skills/kaggle-compete/check-status.sh username/my-notebook --poll --logs

# Check from URL
./skills/kaggle-compete/check-status.sh "https://www.kaggle.com/code/username/my-notebook" --poll
```

| Parameter | Required | Description |
|---|---|---|
| `<kernel_ref>` | Yes | Kernel ref: `username/slug` or Kaggle URL |
| `--poll` | No | Poll until kernel completes or errors |
| `--interval <sec>` | No | Poll interval in seconds (default: 15) |
| `--logs` | No | Show execution logs |

---

### 6. `download-output.sh` — Download notebook output files
Retrieve output files (e.g., submission.csv) from a completed kernel.

```bash
./skills/kaggle-compete/download-output.sh <kernel_ref> [--output <dir>] [--file <name>] [--list]
```

**Examples:**
```bash
# Download all outputs
./skills/kaggle-compete/download-output.sh username/my-notebook --output ./results/

# Download specific file
./skills/kaggle-compete/download-output.sh username/my-notebook --file submission.csv

# List output files
./skills/kaggle-compete/download-output.sh username/my-notebook --list
```

| Parameter | Required | Description |
|---|---|---|
| `<kernel_ref>` | Yes | Kernel ref: `username/slug` or Kaggle URL |
| `--output <dir>` | No | Download directory (default: current dir) |
| `--file <name>` | No | Download specific file only |
| `--list` | No | List output files without downloading |

---

### 7. `list-notebooks.sh` — List notebooks/kernels
Browse and search Kaggle notebooks with various filters.

```bash
./skills/kaggle-compete/list-notebooks.sh [--mine] [--competition <slug>] [--search <query>] [--json]
```

**Examples:**
```bash
# List your own notebooks
./skills/kaggle-compete/list-notebooks.sh --mine

# List notebooks for a competition
./skills/kaggle-compete/list-notebooks.sh --competition titanic

# Search notebooks
./skills/kaggle-compete/list-notebooks.sh --search "random forest" --sort voteCount

# List by user
./skills/kaggle-compete/list-notebooks.sh --user someuser --json
```

| Parameter | Required | Description |
|---|---|---|
| `--mine` | No | List your own notebooks |
| `--user <name>` | No | List notebooks by specific user |
| `--competition <slug>` | No | Filter by competition |
| `--dataset <ref>` | No | Filter by dataset (`owner/slug`) |
| `--search <query>` | No | Search by keyword |
| `--sort <sort>` | No | Sort: hotness, commentCount, dateCreated, dateRun, relevance, voteCount, etc. |
| `--page <n>` | No | Page number (default: 1) |
| `--json` | No | Output as JSON |

---

### 8. `update-notebook.sh` — Update an existing notebook
Modify an existing kernel's source code or metadata while preserving version history.

```bash
./skills/kaggle-compete/update-notebook.sh <kernel_ref> [--notebook <path>] [--title <t>] [--gpu] [--private]
```

**Examples:**
```bash
# Update source code
./skills/kaggle-compete/update-notebook.sh username/my-notebook --notebook updated.ipynb

# Change settings
./skills/kaggle-compete/update-notebook.sh username/my-notebook --gpu --private

# Update title and source
./skills/kaggle-compete/update-notebook.sh username/my-notebook --notebook v2.ipynb --title "Titanic v2"

# Add competition data source
./skills/kaggle-compete/update-notebook.sh username/my-notebook --competition titanic
```

| Parameter | Required | Description |
|---|---|---|
| `<kernel_ref>` | Yes | Kernel ref: `username/slug` or Kaggle URL |
| `--notebook <path>` | No | Update source code from .ipynb file |
| `--title <title>` | No | Set new title |
| `--gpu / --no-gpu` | No | Enable/disable GPU |
| `--internet / --no-internet` | No | Enable/disable internet access |
| `--private / --public` | No | Set visibility |
| `--competition <slug>` | No | Set competition data source |

---

### 9. `get-leaderboard.sh` — View competition leaderboard
Display top entries and find your position on the leaderboard.

```bash
./skills/kaggle-compete/get-leaderboard.sh <competition> [--top <n>] [--json]
```

**Examples:**
```bash
# Show top 20
./skills/kaggle-compete/get-leaderboard.sh titanic

# Show top 10 as JSON
./skills/kaggle-compete/get-leaderboard.sh titanic --top 10 --json

# From URL
./skills/kaggle-compete/get-leaderboard.sh "https://www.kaggle.com/competitions/titanic" --top 50
```

| Parameter | Required | Description |
|---|---|---|
| `<competition>` | Yes | Competition URL or slug |
| `--top <n>` | No | Number of entries to show (default: 20) |
| `--json` | No | Output as JSON |

**Output:** Shows rank, team name, score, and date. Highlights your position if you are on the leaderboard.

---

## Manual Step Required

Before submitting to or downloading data from a competition, you must:
1. Visit the competition URL in a browser
2. Click "Join Competition" and accept the rules

This is a Kaggle limitation -- rules must be accepted through the web UI.

## Technical Notes

- All scripts use `kagglesdk` Python library for KGAT token compatibility
- Both KGAT tokens (new format starting with `KGAT_`) and legacy API keys are supported
- Credentials are sourced from workspace `.env` file
- Default output format is human-readable tables; use `--json` for machine-readable output
- Notebook URL is saved to `temp/notebook_url.txt` by `run.sh`
- Competition dataset path on Kaggle is `/kaggle/input/competitions/{competition-slug}/`
