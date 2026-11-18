CREATE DATABASE IF NOT EXISTS job_tracker;
USE job_tracker;

DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

CREATE TABLE companies (
    company_id INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry VARCHAR(50),
    website VARCHAR(200),
    city VARCHAR(50),
    state VARCHAR(50),
    notes TEXT
);

CREATE TABLE jobs (
    job_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    job_title VARCHAR(100) NOT NULL,
    job_type ENUM('Full-time', 'Part-time', 'Contract', 'Internship'),
    salary_min INT,
    salary_max INT,
    job_url VARCHAR(300),
    date_posted DATE,
    requirements JSON,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE TABLE applications (
    application_id INT PRIMARY KEY AUTO_INCREMENT,
    job_id INT NOT NULL,
    application_date DATE NOT NULL,
    status ENUM('Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn') NOT NULL DEFAULT 'Applied',
    resume_version VARCHAR(50),
    cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE,
    interview_data JSON,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE contacts (
    contact_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE
);

CREATE INDEX idx_jobs_title ON jobs(job_title);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_companies_industry ON companies(industry);

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('Tech Solutions Inc', 'Technology', 'https://www.techsolutions.com', 'Miami', 'Florida', 'Referred by a career fair contact'),
('Data Analytics Corp', 'Data Science', 'https://www.dataanalytics.com', 'Austin', 'Texas', NULL),
('Cloud Systems LLC', 'Cloud Computing', 'https://www.cloudsystems.com', 'Seattle', 'Washington', 'Fully remote friendly'),
('Digital Innovations', 'Software', 'https://www.digitalinnovations.com', 'San Francisco', 'California', NULL),
('Smart Tech Group', 'AI/ML', 'https://www.smarttech.com', 'Boston', 'Massachusetts', 'Research-heavy team');

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer', 'Full-time', 70000, 90000, 'https://www.techsolutions.com/careers/software-developer', '2026-10-15', '["Python", "SQL", "Flask"]'),
(1, 'Database Administrator', 'Full-time', 75000, 95000, 'https://www.techsolutions.com/careers/dba', '2026-10-10', '["SQL", "MySQL", "Linux"]'),
(2, 'Data Analyst', 'Full-time', 65000, 85000, 'https://www.dataanalytics.com/jobs/analyst', '2026-10-12', '["SQL", "Python", "Tableau"]'),
(3, 'Cloud Engineer', 'Full-time', 80000, 100000, 'https://www.cloudsystems.com/jobs/cloud-engineer', '2026-10-08', '["AWS", "Python", "Docker", "Linux"]'),
(4, 'Junior Developer', 'Full-time', 55000, 70000, 'https://www.digitalinnovations.com/jobs/junior', '2026-10-14', '["JavaScript", "HTML", "CSS"]'),
(4, 'Software Engineering Intern', 'Internship', 30000, 40000, 'https://www.digitalinnovations.com/jobs/intern', '2026-10-20', '["Python", "Git"]'),
(5, 'ML Engineer', 'Full-time', 90000, 115000, 'https://www.smarttech.com/careers/ml-engineer', '2026-10-11', '["Python", "SQL", "TensorFlow", "Statistics"]'),
(3, 'Technical Writer', 'Contract', 55000, 75000, NULL, '2026-10-18', '["Documentation", "Git"]');

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data) VALUES
(1, '2026-10-16', 'Applied', 'v2.1', TRUE, NULL),
(3, '2026-10-13', 'Interview', 'v2.1', TRUE, '{"interview_rounds": 2, "interviewers": ["Sarah Johnson", "Mike Chen"], "feedback": "Strong technical skills, good communication", "next_steps": "Final round scheduled"}'),
(4, '2026-10-09', 'Rejected', 'v2.0', FALSE, '{"interview_rounds": 1, "interviewers": ["Emily Williams"], "feedback": "Needs more cloud experience"}'),
(5, '2026-10-15', 'Screening', 'v2.1', TRUE, NULL),
(7, '2026-10-12', 'Offer', 'v2.1', TRUE, '{"interview_rounds": 3, "interviewers": ["Lisa Garcia"], "feedback": "Excellent fit", "next_steps": "Review offer letter"}'),
(6, '2026-10-21', 'Applied', 'v3.0', TRUE, NULL);

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes) VALUES
(1, 'Sarah Johnson', 'HR Manager', 'sjohnson@techsolutions.com', '305-555-0101', 'https://www.linkedin.com/in/sarah-johnson', 'Met at career fair'),
(2, 'Michael Chen', 'Technical Recruiter', 'mchen@dataanalytics.com', NULL, NULL, NULL),
(3, 'Emily Williams', 'Hiring Manager', 'ewilliams@cloudsystems.com', '206-555-0133', NULL, NULL),
(4, 'David Brown', 'Senior Developer', NULL, NULL, NULL, 'Prefers phone calls'),
(5, 'Lisa Garcia', 'Talent Acquisition', 'lgarcia@smarttech.com', '617-555-0188', 'https://www.linkedin.com/in/lisa-garcia', NULL);
