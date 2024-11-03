# setup_github.ps1

# 1. First, ensure you're in the correct directory
Set-Location -Path "path/to/search_term_analyzer"  # Replace with your actual path

# 2. Initialize git repository
git init

# 3. Create .gitignore file
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

# 4. Add all files to git
git add .

# 5. Create initial commit
git commit -m "Initial commit: Basic project structure and core implementations"

# 6. Create GitHub repository using GitHub CLI (gh)
# Make sure you have GitHub CLI installed and authenticated
# You can install it with: winget install GitHub.cli
gh repo create search-term-analyzer --public --description "Advanced search term analysis pipeline for Google Ads optimization" --source=. --remote=origin --push

# 7. Push the code
git push -u origin main

Write-Host "Repository setup complete! Visit https://github.com/yourusername/search-term-analyzer to see your new repository."

# Optional: Create development branch
git checkout -b development
git push -u origin development