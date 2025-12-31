# Dockerfile for Copilot Terminal Carousel
# Windows container only - requires Windows host with ConPTY support

# Use Windows Server Core as base
FROM mcr.microsoft.com/windows/servercore:ltsc2022

# Set shell to PowerShell
SHELL ["powershell", "-Command", "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue';"]

# Install Python 3.12
RUN Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile 'python-installer.exe' ; \
    Start-Process python-installer.exe -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1' -Wait ; \
    Remove-Item python-installer.exe -Force

# Verify Python installation
RUN python --version

# Set working directory
WORKDIR C:/app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy frontend build
COPY frontend/dist/ ./frontend/dist/

# Copy run script
COPY run.py .

# Create data directory
RUN New-Item -ItemType Directory -Path 'C:/app/data/sessions' -Force ; \
    New-Item -ItemType Directory -Path 'C:/app/data/logs' -Force

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=5000
ENV DATA_DIR=C:/app/data
ENV LOG_FILE=C:/app/data/logs/app.jsonl
ENV ALLOW_NON_LOCALHOST=true

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD powershell -Command "Invoke-WebRequest -Uri 'http://localhost:5000/health' -UseBasicParsing"

# Run the application
ENTRYPOINT ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
