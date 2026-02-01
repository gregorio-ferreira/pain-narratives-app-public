# PowerShell script to initialize UV environment and install dependencies

Write-Host "🚀 Initializing Pain Narratives project with UV..." -ForegroundColor Green

# Navigate to project root
Set-Location "c:\Users\jgfer\OneDrive\Documents\my Work\uoc\Proyectos\pain_narratives"

# Initialize UV project (this will create .venv and install dependencies)
Write-Host "📦 Creating virtual environment and installing dependencies..." -ForegroundColor Yellow
uv sync

# Activate the virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

# Verify installation
Write-Host "✅ Verifying installation..." -ForegroundColor Yellow
uv run python -c "import pandas, openai, streamlit, plotly; print('All core dependencies installed successfully!')"

# Test the package import
Write-Host "🧪 Testing package imports..." -ForegroundColor Yellow
uv run python -c "from src.pain_narratives.config.settings import get_settings; print('Package imports working!')"

Write-Host "🎉 Setup complete! You can now run:" -ForegroundColor Green
Write-Host "  uv run streamlit run scripts/run_app.py" -ForegroundColor Cyan

# Optionally start Streamlit
$startStreamlit = Read-Host "Would you like to start the Streamlit app now? (y/n)"
if ($startStreamlit -eq "y" -or $startStreamlit -eq "Y") {
    Write-Host "🌐 Starting Streamlit app..." -ForegroundColor Green
    uv run streamlit run scripts/run_app.py
}
