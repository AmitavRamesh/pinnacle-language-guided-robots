# Run once per terminal:  . D:\pinnacle\env.ps1
# Activates the venv and keeps all caches / downloads / temp on D:\pinnacle\.cache
$c = "D:\pinnacle\.cache"
$env:HF_HOME = "$c\hf"; $env:HF_HUB_CACHE = "$c\hf\hub"; $env:TORCH_HOME = "$c\torch"
$env:YOLO_CONFIG_DIR = "$c\ultralytics"; $env:MPLCONFIGDIR = "$c\mpl"; $env:PIP_CACHE_DIR = "$c\pip"
$env:TMP = "$c\tmp"; $env:TEMP = "$c\tmp"
. D:\pinnacle\.venv\Scripts\Activate.ps1
Set-Location D:\pinnacle\sim
