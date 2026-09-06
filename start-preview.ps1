$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = (Get-Command python -ErrorAction Stop).Source
& $python (Join-Path $root 'app.py') serve --host 127.0.0.1 --port 4346
