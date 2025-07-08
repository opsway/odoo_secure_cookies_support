# Odoo Repository Creation Manual

## Purpose

This guide defines standardized repository creation steps ensure consistency, security, and maintainability across
engineering teams.

## **Create the Repository**

1. Navigate to the following URL:
   [https://github.com/opsway/odoo-boilerplate](https://github.com/opsway/odoo-boilerplate)
2. Create a new repository using the template:
    * Click the **“+”** button in the upper-right corner of the GitHub interface.
    * Select **“New repository”**.
    * In the **“Repository name”** field, enter the desired name in the format: odoo-project-name
    * Complete any remaining fields as required.
    * Confirm creation.

## **Configure Collaborators**

1. In the newly created repository, navigate to:
   **Settings** \> **Collaborators and teams**
2. Add Project team members to the repository: Tech Lead (Admin Role), Project Leader (Maintainer Role), Developer(s) (Maintainer Role).

## **Define Branch Protection Rules**

Configure branch rules for **main** and **staging** branches as specified below:

### **Main Branch Rules**

* **Bypass Permissions:**
    * Allow bypass for the organization and repository administrators.
* **Deletion Restrictions:**
    * Restrict branch deletions.
* **Force Push Restrictions:**
    * Restrict force pushes.
* **Pull Request Requirements:**
    * Require pull request before merging.
    * Require at least **1 approval**.
    * Require approval of the most recent reviewable push.
    * Require resolution of all conversations before merging.
* **Merge Options:**
    * Allow merge commits and squash merging.

### **Staging Branch Rules**

* **Bypass Permissions:**
    * Allow bypass for the organization and repository administrators.
* **Deletion Restrictions:**
    * Restrict branch deletions.
* **Force Push Restrictions:**
    * Restrict force pushes.
* **Pull Request Requirements:**
    * Require pull request before merging.
* **Merge Options:**
    * Allow merge commits and squash merging.

## **Configure Repository Variables**

Set repository-level variables under:
**Settings** \> **Secrets and variables** \> **Actions**

Define the following variables:

* **ODOO\_BRANCH**
    * Description: Major Odoo version branch.
    * Example value: 18.0
* **ENTERPRISE\_REVISION**
    * Description: Odoo Enterprise revision hash.
    * Reference location:
      *Odoo.sh → Branches → Settings → Odoo Version → Repository revisions → enterprise*
    * Example value: 6930ca61007fa9de5cd3fece65465023e40815a4
* **INITIAL\_ODOO\_ADDONS**
    * Description: List of addons to install during the CI process.
    * Example value: ci\_init

### **Variables for supporting AI automations**

* **AI_PR_AUTHOR**
    * Description: GitHub username of the AI agent creating PRs (e.g. `many2none`)
* **JIRA_URL**
    * Description: URL of your Jira instance (e.g. `https://lumirang.atlassian.net`)
* **JIRA_USERNAME**
    * Description: Username/email for Jira (e.g. `ai_agent@opsway.com`)
* **STAGE_BRANCH**
    * Description: Name of the staging branch (e.g. `stage`, `main`, or `master`)
* **DOCKER_COMPOSE_DIR**
    * Description: Path to the directory containing your `docker-compose.yml`
* **ENTERPRISE_DIR**
    * Description: Path to your Odoo Enterprise code checkout, e.g. 'enterprise'
* **ODOO_SERVICE_NAME**
    * Description: Name of the Odoo service in your Docker Compose file (e.g. `regency-web`)
* **DATABASE_SERVICE_NAME**
    * Description: Name of the PostgreSQL service in Docker Compose (e.g. `regency-db`)

## **Configure Repository Secrets**

Add the following secret under:
**Settings** \> **Secrets and variables** \> **Actions**

* **ODOO\_ENTERPRISE\_SECRET**
    * Description: Private key used for Odoo Enterprise continuous integration deployment.

### **Secrets for supporting AI automations**

* **ANTHROPIC_API_KEY**
    * Description: API key for Anthropic/Claude integration
* **GH_PAT**
    * Description: AI agent's GitHub Personal Access Token (for workflow operations)
* **JIRA_API_TOKEN**
    * Description: Token of the AI agent's Jira user (e.g. ai_agent@opsway.com)
* **OPENAI_API_KEY**
    * Description: API key for OpenAI (used by ticket-review workflow)
