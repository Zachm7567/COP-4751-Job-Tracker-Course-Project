# Job Application Tracker

A full-stack web application for tracking job applications. Built for COP4751 with MySQL, Python/Flask and HTML/CSS.

## Features

- Dashboard with totals, response rate, applications by status, recent applications and top companies
- Full CRUD (create, list, detail view, edit, delete with confirmation) for companies, jobs, applications and contacts
- Server-side validation (required fields, valid dates, valid email and URL formats, salary range, valid status and job type, existing foreign keys)
- JSON columns: `jobs.requirements` (required skills) and `applications.interview_data` (rounds, interviewers, feedback, next steps)
- Job Match: enter your skills and see jobs ranked by match percentage, with matched and missing skills
- Search on companies, jobs and contacts, and a status filter on applications

## Requirements

- Python 3.9 or newer
- MySQL 8.0 or newer, running locally
- A MySQL user that can create databases (the examples use `root`)

## Setup

1. Clone the repository and enter the folder.

   ```
   git clone <repository-url>
   cd job-application-tracker
   ```

2. Create a virtual environment and install the dependencies.

   macOS / Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Windows:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create the database and load the sample data. This drops and recreates the four tables in a database named `job_tracker`.

   ```
   mysql -u root -p < schema.sql
   ```

   Alternatively, open `schema.sql` in MySQL Workbench and run the whole script.

4. Tell the app how to connect. Only the password is required if your MySQL user is `root` on `localhost`.

   macOS / Linux:
   ```
   export DB_PASSWORD='your-mysql-password'
   ```

   Windows (Command Prompt):
   ```
   set DB_PASSWORD=your-mysql-password
   ```

   Optional variables: `DB_HOST` (default `localhost`), `DB_PORT` (default `3306`), `DB_USER` (default `root`), `DB_NAME` (default `job_tracker`), `PORT` (default `5001`).

5. Start the app.

   ```
   python app.py
   ```

6. Open http://127.0.0.1:5001 in a browser.

The app uses port 5001 because macOS reserves port 5000 for AirPlay Receiver.

## Database schema

| Table | Purpose | Key columns |
|---|---|---|
| `companies` | Employers | `company_id` (PK), `company_name`, `industry`, `website`, `city`, `state`, `notes` |
| `jobs` | Job postings | `job_id` (PK), `company_id` (FK), `job_title`, `job_type` (ENUM), `salary_min`, `salary_max`, `job_url`, `date_posted`, `requirements` (JSON) |
| `applications` | Applications you submitted | `application_id` (PK), `job_id` (FK), `application_date`, `status` (ENUM), `resume_version`, `cover_letter_sent`, `interview_data` (JSON) |
| `contacts` | People at companies | `contact_id` (PK), `company_id` (FK), `contact_name`, `title`, `email`, `phone`, `linkedin_url`, `notes` |

One company has many jobs and many contacts. One job has many applications. Foreign keys use `ON DELETE CASCADE`, so deleting a company removes its jobs, applications and contacts (the app asks for confirmation first).

Indexes: `idx_jobs_title`, `idx_applications_status`, `idx_companies_industry`.

## Job Match

Skills are stored on each job as a JSON array, for example `["Python", "SQL", "Flask"]`. For every job, the match percentage is the number of required skills you listed divided by the number of skills the job requires. Matching ignores case. Jobs are sorted from highest to lowest percentage.

## Project structure

```
app.py              Flask routes, validation and Job Match logic
database.py         MySQL connection and query helpers
schema.sql          Creates the database, tables, indexes and sample data
templates/          Jinja2 HTML templates
static/style.css    Stylesheet
requirements.txt    Python dependencies
```

## Troubleshooting

- "Access denied": set `DB_PASSWORD` (and `DB_USER` if you do not use `root`).
- "Unknown database": run `schema.sql` first.
- Port already in use: set `PORT` to another number, for example `PORT=5002 python app.py`.
