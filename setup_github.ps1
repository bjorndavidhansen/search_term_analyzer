# setup_github_fixed.ps1

# 1. Check if GitHub CLI is installed, if not install it
if (!(Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI not found. Installing..."
    winget install GitHub.cli
    Write-Host "Please restart PowerShell after installation and run this script again."
    exit
}

# 2. Check if authenticated with GitHub
$ghAuthStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please authenticate with GitHub first by running: gh auth login"
    exit
}

# 3. Initialize git repository (if not already initialized)
if (!(Test-Path .git)) {
    git init
    Write-Host "Git repository initialized"
}

# 4. Create .gitignore file (if not exists)
if (!(Test-Path .gitignore)) {
    @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/
.env

# IDE
.idea/
.vscode/
*.swp
*.swo

# Logs and databases
*.log
*.sqlite
*.db

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
cache/
logs/
data/
"@ | Out-File -FilePath ".gitignore" -Encoding utf8
    Write-Host ".gitignore created"
}

# 5. Add all files to git
git add .

# 6. Create initial commit (if needed)
$hasCommits = git log -n 1 2>$null
if (!$hasCommits) {
    git commit -m "Initial commit: Basic project structure and core implementations"
    Write-Host "Initial commit created"
}

# 7. Create GitHub repository and push
Write-Host "Creating GitHub repository..."
gh repo create search-term-analyzer --public --description "Advanced search term analysis pipeline for Google Ads optimization" --source=. --remote=origin

# 8. Push the code
git branch -M main
git push -u origin main

Write-Host "Repository setup complete!"

# 9. Create development branch
git checkout -b development
git push -u origin development

Write-Host "Development branch created and pushed!"