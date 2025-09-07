function Run-Command {
    param($cmd)
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

Run-Command "uv run pytest"
Run-Command "uv run ruff check ."
Run-Command "uv run ruff format --check ."
Run-Command "uv run pyright ."
