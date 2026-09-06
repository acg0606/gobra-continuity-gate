$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = (Get-Command python -ErrorAction Stop).Source
$env:PYTHONPATH = (@(
    $root
    (Join-Path $root 'vendor')
) -join [IO.Path]::PathSeparator)
& $python -m unittest discover -s (Join-Path $root 'tests') -v
& $python (Join-Path $root 'app.py') --database (Join-Path $root '.continuity\verification.db') demo
