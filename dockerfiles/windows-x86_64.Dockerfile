# escape=`

FROM mcr.microsoft.com/windows/server:ltsc2025

SHELL ["powershell", "-Command"]

RUN `
    New-Item -Path "C:\TEMP" -ItemType Directory;`
    # Download the Build Tools bootstrapper.`
    Invoke-WebRequest -Uri 'https://aka.ms/vs/stable/vs_buildtools.exe' -OutFile 'C:\TEMP\vs_buildtools.exe'; `
    `
    # Install Build Tools with the Microsoft.VisualStudio.Workload.VCTools workload`
    $p = Start-Process -FilePath 'C:\TEMP\vs_buildtools.exe' -Wait -PassThru `
        -ArgumentList '--quiet', '--wait', '--norestart', '--nocache', '--add', 'Microsoft.VisualStudio.Workload.VCTools'; `
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) { exit $p.ExitCode }; `
    `
    # Cleanup`
    Remove-Item -Force 'C:\TEMP\vs_buildtools.exe'


# Download and install uv
# Unwind this when the runner is re-implemented in C++
RUN irm https://astral.sh/uv/install.ps1 | iex

# Add uv to the System PATH
# The leading $null is to avoid a dockerfile parsing issue that treats angle brackets specially.
RUN $null = [Environment]::SetEnvironmentVariable('PATH', 'C:\Users\ContainerUser\.local\bin;' + $env:PATH, [EnvironmentVariableTarget]::Machine)

COPY src 'C:\cimple\src'
COPY pyproject.toml 'C:\cimple\pyproject.toml'
COPY uv.lock 'C:\cimple\uv.lock'

RUN cd 'C:\cimple'; uv sync

# Add cimple system root to the System PATH
RUN $null = [Environment]::SetEnvironmentVariable('PATH', 'C:\cimple-root\bin;' + $env:PATH, [EnvironmentVariableTarget]::Machine)

WORKDIR 'C:\cimple'
