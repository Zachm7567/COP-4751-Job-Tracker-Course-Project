import json
import os
import re
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for, abort
from mysql.connector import Error as MySQLError

import database as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

JOB_TYPES = ['Full-time', 'Part-time', 'Contract', 'Internship']
STATUSES = ['Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn']
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def clean(value):
    value = (value or '').strip()
    return value or None


def parse_json(value):
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8')
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def skill_list(value):
    data = parse_json(value)
    if isinstance(data, dict):
        data = data.get('required_skills') or data.get('skills') or []
    if not isinstance(data, list):
        return []
    seen = set()
    skills = []
    for item in data:
        skill = str(item).strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def split_list(text):
    seen = set()
    items = []
    for part in re.split(r'[,\n]', text or ''):
        part = part.strip()
        if part and part.lower() not in seen:
            seen.add(part.lower())
            items.append(part)
    return items


def read_text(form, name, label, errors, required=False, max_length=None):
    value = clean(form.get(name))
    if value is None:
        if required:
            errors.append(f'{label} is required.')
        return None
    if max_length and len(value) > max_length:
        errors.append(f'{label} must be {max_length} characters or fewer.')
    return value


def read_int(form, name, label, errors, required=False):
    value = clean(form.get(name))
    if value is None:
        if required:
            errors.append(f'{label} is required.')
        return None
    try:
        number = int(value)
    except ValueError:
        errors.append(f'{label} must be a whole number.')
        return None
    if number < 0:
        errors.append(f'{label} cannot be negative.')
        return None
    return number


def read_date(form, name, label, errors, required=False):
    value = clean(form.get(name))
    if value is None:
        if required:
            errors.append(f'{label} is required.')
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(f'{label} must be a valid date.')
        return None
    return value


def read_url(form, name, label, errors, max_length):
    value = read_text(form, name, label, errors, max_length=max_length)
    if value and not re.match(r'^https?://', value, re.IGNORECASE):
        errors.append(f'{label} must start with http:// or https://.')
    return value


def read_choice(form, name, label, choices, errors, required=False):
    value = clean(form.get(name))
    if value is None:
        if required:
            errors.append(f'{label} is required.')
        return None
    if value not in choices:
        errors.append(f'{label} is not a valid choice.')
        return None
    return value


def read_foreign_key(form, name, label, table, key, errors):
    value = read_int(form, name, label, errors, required=True)
    if value is not None and not db.fetch_one(f'SELECT {key} FROM {table} WHERE {key} = %s', (value,)):
        errors.append(f'{label} does not exist.')
        return None
    return value


def field(name, label, kind='text', value='', required=False, options=None, placeholder='', hint=''):
    return {
        'name': name,
        'label': label,
        'kind': kind,
        'value': '' if value is None else value,
        'required': required,
        'options': options or [],
        'placeholder': placeholder,
        'hint': hint,
    }


def show_errors(errors):
    for message in errors:
        flash(message, 'error')


@app.errorhandler(MySQLError)
def database_error(error):
    return render_template('error.html', message=str(error)), 500


@app.route('/')
def dashboard():
    counts = db.fetch_one(
        'SELECT (SELECT COUNT(*) FROM companies) AS companies, '
        '(SELECT COUNT(*) FROM jobs) AS jobs, '
        '(SELECT COUNT(*) FROM applications) AS applications, '
        '(SELECT COUNT(*) FROM contacts) AS contacts'
    )
    status_rows = db.fetch_all(
        'SELECT status, COUNT(*) AS total FROM applications GROUP BY status'
    )
    by_status = {row['status']: row['total'] for row in status_rows}
    status_counts = [{'status': s, 'total': by_status.get(s, 0)} for s in STATUSES]
    total_apps = counts['applications']
    responded = total_apps - by_status.get('Applied', 0)
    response_rate = round(responded * 100 / total_apps) if total_apps else 0
    max_status = max([row['total'] for row in status_counts] + [1])
    recent = db.fetch_all(
        'SELECT a.application_id, a.application_date, a.status, j.job_title, c.company_name '
        'FROM applications a JOIN jobs j ON a.job_id = j.job_id '
        'JOIN companies c ON j.company_id = c.company_id '
        'ORDER BY a.application_date DESC, a.application_id DESC LIMIT 5'
    )
    top_companies = db.fetch_all(
        'SELECT c.company_id, c.company_name, COUNT(j.job_id) AS total '
        'FROM companies c LEFT JOIN jobs j ON c.company_id = j.company_id '
        'GROUP BY c.company_id, c.company_name ORDER BY total DESC, c.company_name LIMIT 5'
    )
    salary = db.fetch_one(
        'SELECT ROUND(AVG(salary_min)) AS low, ROUND(AVG(salary_max)) AS high '
        'FROM jobs WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL'
    )
    return render_template(
        'dashboard.html',
        counts=counts,
        status_counts=status_counts,
        max_status=max_status,
        response_rate=response_rate,
        recent=recent,
        top_companies=top_companies,
        salary=salary,
    )


def company_fields(values):
    return [
        field('company_name', 'Company Name', value=values.get('company_name'), required=True),
        field('industry', 'Industry', value=values.get('industry')),
        field('website', 'Website', 'url', values.get('website'), placeholder='https://'),
        field('city', 'City', value=values.get('city')),
        field('state', 'State', value=values.get('state')),
        field('notes', 'Notes', 'textarea', values.get('notes')),
    ]


def read_company(form):
    errors = []
    data = (
        read_text(form, 'company_name', 'Company name', errors, True, 100),
        read_text(form, 'industry', 'Industry', errors, max_length=50),
        read_url(form, 'website', 'Website', errors, 200),
        read_text(form, 'city', 'City', errors, max_length=50),
        read_text(form, 'state', 'State', errors, max_length=50),
        read_text(form, 'notes', 'Notes', errors),
    )
    return data, errors


@app.route('/companies')
def companies():
    search = clean(request.args.get('q'))
    sql = (
        'SELECT c.*, COUNT(DISTINCT j.job_id) AS job_count, COUNT(DISTINCT ct.contact_id) AS contact_count '
        'FROM companies c LEFT JOIN jobs j ON c.company_id = j.company_id '
        'LEFT JOIN contacts ct ON c.company_id = ct.company_id '
    )
    params = ()
    if search:
        sql += 'WHERE c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s '
        like = f'%{search}%'
        params = (like, like, like)
    sql += 'GROUP BY c.company_id ORDER BY c.company_name'
    return render_template('companies.html', companies=db.fetch_all(sql, params), search=search or '')


@app.route('/companies/new', methods=['GET', 'POST'])
def company_new():
    values = request.form if request.method == 'POST' else {}
    if request.method == 'POST':
        data, errors = read_company(request.form)
        if not errors:
            new_id = db.execute(
                'INSERT INTO companies (company_name, industry, website, city, state, notes) '
                'VALUES (%s, %s, %s, %s, %s, %s)', data
            )
            flash('Company added.', 'success')
            return redirect(url_for('company_detail', company_id=new_id))
        show_errors(errors)
    return render_template('form.html', title='Add Company', fields=company_fields(values),
                           cancel_url=url_for('companies'), submit_label='Add Company')


@app.route('/companies/<int:company_id>')
def company_detail(company_id):
    company = db.fetch_one('SELECT * FROM companies WHERE company_id = %s', (company_id,))
    if not company:
        abort(404)
    jobs = db.fetch_all(
        'SELECT job_id, job_title, job_type FROM jobs WHERE company_id = %s ORDER BY job_title', (company_id,)
    )
    contacts = db.fetch_all(
        'SELECT contact_id, contact_name, title FROM contacts WHERE company_id = %s ORDER BY contact_name',
        (company_id,)
    )
    rows = [
        ('Industry', company['industry']),
        ('Website', company['website']),
        ('City', company['city']),
        ('State', company['state']),
        ('Notes', company['notes']),
    ]
    related = [
        {'heading': 'Jobs', 'items': [
            {'text': f"{j['job_title']} ({j['job_type'] or 'n/a'})", 'url': url_for('job_detail', job_id=j['job_id'])}
            for j in jobs]},
        {'heading': 'Contacts', 'items': [
            {'text': f"{c['contact_name']} - {c['title'] or 'n/a'}", 'url': url_for('contact_detail', contact_id=c['contact_id'])}
            for c in contacts]},
    ]
    return render_template(
        'detail.html', title=company['company_name'], rows=rows, related=related,
        edit_url=url_for('company_edit', company_id=company_id),
        delete_url=url_for('company_delete', company_id=company_id),
        back_url=url_for('companies'),
        confirm='Delete this company along with its jobs, applications and contacts?'
    )


@app.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
def company_edit(company_id):
    company = db.fetch_one('SELECT * FROM companies WHERE company_id = %s', (company_id,))
    if not company:
        abort(404)
    values = company
    if request.method == 'POST':
        values = request.form
        data, errors = read_company(request.form)
        if not errors:
            db.execute(
                'UPDATE companies SET company_name=%s, industry=%s, website=%s, city=%s, state=%s, notes=%s '
                'WHERE company_id=%s', data + (company_id,)
            )
            flash('Company updated.', 'success')
            return redirect(url_for('company_detail', company_id=company_id))
        show_errors(errors)
    return render_template('form.html', title='Edit Company', fields=company_fields(values),
                           cancel_url=url_for('company_detail', company_id=company_id), submit_label='Save Changes')


@app.route('/companies/<int:company_id>/delete', methods=['POST'])
def company_delete(company_id):
    db.execute('DELETE FROM companies WHERE company_id = %s', (company_id,))
    flash('Company deleted.', 'success')
    return redirect(url_for('companies'))


def company_options():
    rows = db.fetch_all('SELECT company_id, company_name FROM companies ORDER BY company_name')
    return [(str(r['company_id']), r['company_name']) for r in rows]


def job_fields(values):
    skills = values.get('requirements')
    if not isinstance(skills, str):
        skills = ', '.join(skill_list(skills))
    return [
        field('company_id', 'Company', 'select', str(values.get('company_id') or ''), True, company_options()),
        field('job_title', 'Job Title', value=values.get('job_title'), required=True),
        field('job_type', 'Job Type', 'select', values.get('job_type'), False, [(t, t) for t in JOB_TYPES]),
        field('salary_min', 'Minimum Salary', 'number', values.get('salary_min')),
        field('salary_max', 'Maximum Salary', 'number', values.get('salary_max')),
        field('job_url', 'Job URL', 'url', values.get('job_url'), placeholder='https://'),
        field('date_posted', 'Date Posted', 'date', values.get('date_posted')),
        field('requirements', 'Required Skills', 'textarea', skills,
              placeholder='Python, SQL, Flask', hint='Separate skills with commas. Used by Job Match.'),
    ]


def read_job(form):
    errors = []
    company_id = read_foreign_key(form, 'company_id', 'Company', 'companies', 'company_id', errors)
    title = read_text(form, 'job_title', 'Job title', errors, True, 100)
    job_type = read_choice(form, 'job_type', 'Job type', JOB_TYPES, errors)
    salary_min = read_int(form, 'salary_min', 'Minimum salary', errors)
    salary_max = read_int(form, 'salary_max', 'Maximum salary', errors)
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        errors.append('Minimum salary cannot be greater than maximum salary.')
    url = read_url(form, 'job_url', 'Job URL', errors, 300)
    posted = read_date(form, 'date_posted', 'Date posted', errors)
    skills = split_list(form.get('requirements'))
    requirements = json.dumps(skills) if skills else None
    data = (company_id, title, job_type, salary_min, salary_max, url, posted, requirements)
    return data, errors


@app.route('/jobs')
def jobs():
    search = clean(request.args.get('q'))
    sql = (
        'SELECT j.*, c.company_name, COUNT(a.application_id) AS application_count '
        'FROM jobs j JOIN companies c ON j.company_id = c.company_id '
        'LEFT JOIN applications a ON j.job_id = a.job_id '
    )
    params = ()
    if search:
        sql += 'WHERE j.job_title LIKE %s OR c.company_name LIKE %s '
        like = f'%{search}%'
        params = (like, like)
    sql += 'GROUP BY j.job_id, c.company_name ORDER BY j.date_posted DESC, j.job_id DESC'
    rows = db.fetch_all(sql, params)
    for row in rows:
        row['skills'] = skill_list(row['requirements'])
    return render_template('jobs.html', jobs=rows, search=search or '')


@app.route('/jobs/new', methods=['GET', 'POST'])
def job_new():
    values = request.form if request.method == 'POST' else {}
    if request.method == 'POST':
        data, errors = read_job(request.form)
        if not errors:
            new_id = db.execute(
                'INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, '
                'date_posted, requirements) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', data
            )
            flash('Job added.', 'success')
            return redirect(url_for('job_detail', job_id=new_id))
        show_errors(errors)
    return render_template('form.html', title='Add Job', fields=job_fields(values),
                           cancel_url=url_for('jobs'), submit_label='Add Job')


@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    job = db.fetch_one(
        'SELECT j.*, c.company_name FROM jobs j JOIN companies c ON j.company_id = c.company_id '
        'WHERE j.job_id = %s', (job_id,)
    )
    if not job:
        abort(404)
    applications = db.fetch_all(
        'SELECT application_id, application_date, status FROM applications WHERE job_id = %s '
        'ORDER BY application_date DESC', (job_id,)
    )
    salary = None
    if job['salary_min'] is not None or job['salary_max'] is not None:
        low = f"${job['salary_min']:,}" if job['salary_min'] is not None else '?'
        high = f"${job['salary_max']:,}" if job['salary_max'] is not None else '?'
        salary = f'{low} - {high}'
    rows = [
        ('Company', job['company_name']),
        ('Job Type', job['job_type']),
        ('Salary', salary),
        ('Job URL', job['job_url']),
        ('Date Posted', job['date_posted']),
        ('Required Skills', ', '.join(skill_list(job['requirements']))),
    ]
    related = [{'heading': 'Applications', 'items': [
        {'text': f"{a['application_date']} - {a['status']}", 'url': url_for('application_detail', application_id=a['application_id'])}
        for a in applications]}]
    return render_template(
        'detail.html', title=job['job_title'], rows=rows, related=related,
        edit_url=url_for('job_edit', job_id=job_id),
        delete_url=url_for('job_delete', job_id=job_id),
        back_url=url_for('jobs'),
        confirm='Delete this job and all of its applications?'
    )


@app.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
def job_edit(job_id):
    job = db.fetch_one('SELECT * FROM jobs WHERE job_id = %s', (job_id,))
    if not job:
        abort(404)
    values = job
    if request.method == 'POST':
        values = request.form
        data, errors = read_job(request.form)
        if not errors:
            db.execute(
                'UPDATE jobs SET company_id=%s, job_title=%s, job_type=%s, salary_min=%s, salary_max=%s, '
                'job_url=%s, date_posted=%s, requirements=%s WHERE job_id=%s', data + (job_id,)
            )
            flash('Job updated.', 'success')
            return redirect(url_for('job_detail', job_id=job_id))
        show_errors(errors)
    return render_template('form.html', title='Edit Job', fields=job_fields(values),
                           cancel_url=url_for('job_detail', job_id=job_id), submit_label='Save Changes')


@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
def job_delete(job_id):
    db.execute('DELETE FROM jobs WHERE job_id = %s', (job_id,))
    flash('Job deleted.', 'success')
    return redirect(url_for('jobs'))


def job_options():
    rows = db.fetch_all(
        'SELECT j.job_id, j.job_title, c.company_name FROM jobs j '
        'JOIN companies c ON j.company_id = c.company_id ORDER BY c.company_name, j.job_title'
    )
    return [(str(r['job_id']), f"{r['company_name']} - {r['job_title']}") for r in rows]


def application_fields(values):
    if hasattr(values, 'getlist'):
        rounds = values.get('interview_rounds')
        interviewers = values.get('interviewers')
        feedback = values.get('feedback')
        next_steps = values.get('next_steps')
    else:
        interview = parse_json(values.get('interview_data')) or {}
        rounds = interview.get('interview_rounds')
        interviewers = ', '.join(interview.get('interviewers') or [])
        feedback = interview.get('feedback')
        next_steps = interview.get('next_steps')
    sent = bool(values.get('cover_letter_sent'))
    return [
        field('job_id', 'Job', 'select', str(values.get('job_id') or ''), True, job_options()),
        field('application_date', 'Application Date', 'date',
              values.get('application_date') or date.today().isoformat(), True),
        field('status', 'Status', 'select', values.get('status') or 'Applied', True, [(s, s) for s in STATUSES]),
        field('resume_version', 'Resume Version', value=values.get('resume_version'), placeholder='v1.0'),
        field('cover_letter_sent', 'Cover letter sent', 'checkbox', sent),
        field('interview_rounds', 'Interview Rounds', 'number', rounds),
        field('interviewers', 'Interviewers', 'text', interviewers, placeholder='Sarah Johnson, Mike Chen',
              hint='Separate names with commas.'),
        field('feedback', 'Interview Feedback', 'textarea', feedback),
        field('next_steps', 'Next Steps', 'text', next_steps),
    ]


def read_application(form):
    errors = []
    job_id = read_foreign_key(form, 'job_id', 'Job', 'jobs', 'job_id', errors)
    applied = read_date(form, 'application_date', 'Application date', errors, True)
    status = read_choice(form, 'status', 'Status', STATUSES, errors, True)
    resume = read_text(form, 'resume_version', 'Resume version', errors, max_length=50)
    sent = 1 if form.get('cover_letter_sent') else 0
    rounds = read_int(form, 'interview_rounds', 'Interview rounds', errors)
    interviewers = split_list(form.get('interviewers'))
    feedback = read_text(form, 'feedback', 'Interview feedback', errors)
    next_steps = read_text(form, 'next_steps', 'Next steps', errors, max_length=200)
    interview = {}
    if rounds is not None:
        interview['interview_rounds'] = rounds
    if interviewers:
        interview['interviewers'] = interviewers
    if feedback:
        interview['feedback'] = feedback
    if next_steps:
        interview['next_steps'] = next_steps
    interview_json = json.dumps(interview) if interview else None
    return (job_id, applied, status, resume, sent, interview_json), errors


@app.route('/applications')
def applications():
    status = clean(request.args.get('status'))
    sql = (
        'SELECT a.*, j.job_title, c.company_name FROM applications a '
        'JOIN jobs j ON a.job_id = j.job_id JOIN companies c ON j.company_id = c.company_id '
    )
    params = ()
    if status in STATUSES:
        sql += 'WHERE a.status = %s '
        params = (status,)
    sql += 'ORDER BY a.application_date DESC, a.application_id DESC'
    return render_template('applications.html', applications=db.fetch_all(sql, params),
                           statuses=STATUSES, selected=status if status in STATUSES else '')


@app.route('/applications/new', methods=['GET', 'POST'])
def application_new():
    values = request.form if request.method == 'POST' else {}
    if request.method == 'POST':
        data, errors = read_application(request.form)
        if not errors:
            new_id = db.execute(
                'INSERT INTO applications (job_id, application_date, status, resume_version, '
                'cover_letter_sent, interview_data) VALUES (%s, %s, %s, %s, %s, %s)', data
            )
            flash('Application added.', 'success')
            return redirect(url_for('application_detail', application_id=new_id))
        show_errors(errors)
    return render_template('form.html', title='Add Application', fields=application_fields(values),
                           cancel_url=url_for('applications'), submit_label='Add Application')


@app.route('/applications/<int:application_id>')
def application_detail(application_id):
    application = db.fetch_one(
        'SELECT a.*, j.job_title, j.job_id, c.company_name, c.company_id FROM applications a '
        'JOIN jobs j ON a.job_id = j.job_id JOIN companies c ON j.company_id = c.company_id '
        'WHERE a.application_id = %s', (application_id,)
    )
    if not application:
        abort(404)
    interview = parse_json(application['interview_data']) or {}
    rows = [
        ('Company', application['company_name']),
        ('Job', application['job_title']),
        ('Application Date', application['application_date']),
        ('Status', application['status']),
        ('Resume Version', application['resume_version']),
        ('Cover Letter Sent', 'Yes' if application['cover_letter_sent'] else 'No'),
        ('Interview Rounds', interview.get('interview_rounds')),
        ('Interviewers', ', '.join(interview.get('interviewers') or [])),
        ('Feedback', interview.get('feedback')),
        ('Next Steps', interview.get('next_steps')),
    ]
    related = [{'heading': 'Related', 'items': [
        {'text': application['job_title'], 'url': url_for('job_detail', job_id=application['job_id'])},
        {'text': application['company_name'], 'url': url_for('company_detail', company_id=application['company_id'])},
    ]}]
    return render_template(
        'detail.html', title=f"{application['job_title']} at {application['company_name']}",
        rows=rows, related=related,
        edit_url=url_for('application_edit', application_id=application_id),
        delete_url=url_for('application_delete', application_id=application_id),
        back_url=url_for('applications'),
        confirm='Delete this application?'
    )


@app.route('/applications/<int:application_id>/edit', methods=['GET', 'POST'])
def application_edit(application_id):
    application = db.fetch_one('SELECT * FROM applications WHERE application_id = %s', (application_id,))
    if not application:
        abort(404)
    values = application
    if request.method == 'POST':
        values = request.form
        data, errors = read_application(request.form)
        if not errors:
            db.execute(
                'UPDATE applications SET job_id=%s, application_date=%s, status=%s, resume_version=%s, '
                'cover_letter_sent=%s, interview_data=%s WHERE application_id=%s', data + (application_id,)
            )
            flash('Application updated.', 'success')
            return redirect(url_for('application_detail', application_id=application_id))
        show_errors(errors)
    return render_template('form.html', title='Edit Application', fields=application_fields(values),
                           cancel_url=url_for('application_detail', application_id=application_id),
                           submit_label='Save Changes')


@app.route('/applications/<int:application_id>/delete', methods=['POST'])
def application_delete(application_id):
    db.execute('DELETE FROM applications WHERE application_id = %s', (application_id,))
    flash('Application deleted.', 'success')
    return redirect(url_for('applications'))


def contact_fields(values):
    return [
        field('company_id', 'Company', 'select', str(values.get('company_id') or ''), True, company_options()),
        field('contact_name', 'Contact Name', value=values.get('contact_name'), required=True),
        field('title', 'Title', value=values.get('title')),
        field('email', 'Email', 'email', values.get('email')),
        field('phone', 'Phone', 'tel', values.get('phone')),
        field('linkedin_url', 'LinkedIn URL', 'url', values.get('linkedin_url'), placeholder='https://'),
        field('notes', 'Notes', 'textarea', values.get('notes')),
    ]


def read_contact(form):
    errors = []
    company_id = read_foreign_key(form, 'company_id', 'Company', 'companies', 'company_id', errors)
    name = read_text(form, 'contact_name', 'Contact name', errors, True, 100)
    title = read_text(form, 'title', 'Title', errors, max_length=100)
    email = read_text(form, 'email', 'Email', errors, max_length=100)
    if email and not EMAIL_PATTERN.match(email):
        errors.append('Email address is not valid.')
    phone = read_text(form, 'phone', 'Phone', errors, max_length=20)
    linkedin = read_url(form, 'linkedin_url', 'LinkedIn URL', errors, 200)
    notes = read_text(form, 'notes', 'Notes', errors)
    return (company_id, name, title, email, phone, linkedin, notes), errors


@app.route('/contacts')
def contacts():
    search = clean(request.args.get('q'))
    sql = 'SELECT ct.*, c.company_name FROM contacts ct JOIN companies c ON ct.company_id = c.company_id '
    params = ()
    if search:
        sql += 'WHERE ct.contact_name LIKE %s OR c.company_name LIKE %s OR ct.email LIKE %s '
        like = f'%{search}%'
        params = (like, like, like)
    sql += 'ORDER BY ct.contact_name'
    return render_template('contacts.html', contacts=db.fetch_all(sql, params), search=search or '')


@app.route('/contacts/new', methods=['GET', 'POST'])
def contact_new():
    values = request.form if request.method == 'POST' else {}
    if request.method == 'POST':
        data, errors = read_contact(request.form)
        if not errors:
            new_id = db.execute(
                'INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)', data
            )
            flash('Contact added.', 'success')
            return redirect(url_for('contact_detail', contact_id=new_id))
        show_errors(errors)
    return render_template('form.html', title='Add Contact', fields=contact_fields(values),
                           cancel_url=url_for('contacts'), submit_label='Add Contact')


@app.route('/contacts/<int:contact_id>')
def contact_detail(contact_id):
    contact = db.fetch_one(
        'SELECT ct.*, c.company_name FROM contacts ct JOIN companies c ON ct.company_id = c.company_id '
        'WHERE ct.contact_id = %s', (contact_id,)
    )
    if not contact:
        abort(404)
    rows = [
        ('Company', contact['company_name']),
        ('Title', contact['title']),
        ('Email', contact['email']),
        ('Phone', contact['phone']),
        ('LinkedIn', contact['linkedin_url']),
        ('Notes', contact['notes']),
    ]
    related = [{'heading': 'Company', 'items': [
        {'text': contact['company_name'], 'url': url_for('company_detail', company_id=contact['company_id'])}]}]
    return render_template(
        'detail.html', title=contact['contact_name'], rows=rows, related=related,
        edit_url=url_for('contact_edit', contact_id=contact_id),
        delete_url=url_for('contact_delete', contact_id=contact_id),
        back_url=url_for('contacts'),
        confirm='Delete this contact?'
    )


@app.route('/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
def contact_edit(contact_id):
    contact = db.fetch_one('SELECT * FROM contacts WHERE contact_id = %s', (contact_id,))
    if not contact:
        abort(404)
    values = contact
    if request.method == 'POST':
        values = request.form
        data, errors = read_contact(request.form)
        if not errors:
            db.execute(
                'UPDATE contacts SET company_id=%s, contact_name=%s, title=%s, email=%s, phone=%s, '
                'linkedin_url=%s, notes=%s WHERE contact_id=%s', data + (contact_id,)
            )
            flash('Contact updated.', 'success')
            return redirect(url_for('contact_detail', contact_id=contact_id))
        show_errors(errors)
    return render_template('form.html', title='Edit Contact', fields=contact_fields(values),
                           cancel_url=url_for('contact_detail', contact_id=contact_id), submit_label='Save Changes')


@app.route('/contacts/<int:contact_id>/delete', methods=['POST'])
def contact_delete(contact_id):
    db.execute('DELETE FROM contacts WHERE contact_id = %s', (contact_id,))
    flash('Contact deleted.', 'success')
    return redirect(url_for('contacts'))


def match_jobs(user_skills):
    wanted = {s.lower() for s in user_skills}
    rows = db.fetch_all(
        'SELECT j.job_id, j.job_title, j.job_type, j.requirements, c.company_name '
        'FROM jobs j JOIN companies c ON j.company_id = c.company_id'
    )
    results = []
    for row in rows:
        required = skill_list(row['requirements'])
        if not required:
            continue
        matched = [s for s in required if s.lower() in wanted]
        missing = [s for s in required if s.lower() not in wanted]
        results.append({
            'job_id': row['job_id'],
            'job_title': row['job_title'],
            'company_name': row['company_name'],
            'job_type': row['job_type'],
            'percent': round(len(matched) * 100 / len(required)),
            'matched': matched,
            'missing': missing,
            'total': len(required),
        })
    results.sort(key=lambda r: (-r['percent'], -len(r['matched']), r['job_title']))
    return results


@app.route('/job-match', methods=['GET', 'POST'])
def job_match():
    skills_text = ''
    results = None
    skills = []
    if request.method == 'POST':
        skills_text = request.form.get('skills', '')
        skills = split_list(skills_text)
        if skills:
            results = match_jobs(skills)
        else:
            flash('Enter at least one skill.', 'error')
    return render_template('job_match.html', skills_text=skills_text, skills=skills, results=results)


if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', '5001')))
