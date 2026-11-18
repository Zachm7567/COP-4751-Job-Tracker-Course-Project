# AI Usage Documentation

## Tools Used

- Claude (Anthropic), used through a chat interface for occasional coding assistance, troubleshooting, database design suggestions, and documentation support.

## Key Prompts

1. Provided the project specification and asked for guidance on organizing the application structure, including the Flask backend, MySQL database, and HTML templates.
2. Asked for assistance reviewing the database schema to ensure it followed the project requirements, including ENUM columns and JSON columns for requirements and interview data.
3. Asked for suggestions on implementing the Job Match feature to compare job requirements against a user's skills and identify missing qualifications.
4. Asked for help improving the README instructions so the application could be set up after a fresh clone.

## What Worked Well

- Claude provided useful suggestions for organizing the application and addressing individual development questions.
- It helped identify ways to structure validation functions and avoid repeating code.
- It provided guidance on using parameterized queries to prevent SQL injection.
- It helped troubleshoot a navigation highlighting issue discovered during testing.

## What I Modified

- Changed the application's brand name in the navigation bar to "Zach's Job Tracker" (templates/base.html).
- Changed the color theme from blue to teal by editing the --primary and --primary-dark colors in static/style.css.
- Configured the application to run against my own local MySQL server and tested the CRUD functionality across all four tables.
- Tested Job Match using my own skill information.
- Fixed local setup problems, including MySQL password and port conflicts, and configured DB_PASSWORD as an environment variable.

## Lessons Learned

- Suggestions from AI tools are most useful when applied to specific development problems.
- Generated code and recommendations should always be reviewed and tested.
- Understanding the database structure and application logic is important when making changes.
- Database configuration and environment variables require proper setup outside the application code.
- AI can be useful for troubleshooting and development guidance, but the final implementation still needs to be verified.
