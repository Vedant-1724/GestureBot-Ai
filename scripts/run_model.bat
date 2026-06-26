@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo ================================================
echo GC-Car Live Model Launcher
echo ================================================
echo.

if not exist "gc_car_env\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Recreate with:
    echo   py -3.11 -m venv gc_car_env
    echo   gc_car_env\Scripts\activate
    echo   pip install -r requirements.txt
    echo   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    echo.
    pause
    exit /b 1
)

if not exist "models\gc_car_trained_model\gc_car_yolo11m_best.pt" (
    echo [ERROR] Trained model not found at:
    echo         models\gc_car_trained_model\gc_car_yolo11m_best.pt
    echo.
    pause
    exit /b 1
)

call "gc_car_env\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Could not activate gc_car_env.
    pause
    exit /b 1
)

set "ESP32_IP=192.168.1.100"
set /p "USER_INPUT=Enter ESP32-CAM IP or type local for webcam [192.168.1.100]: "

if not "%USER_INPUT%"=="" set "ESP32_IP=%USER_INPUT%"

echo.
if /I "%ESP32_IP%"=="local" (
    echo [INFO] Starting local webcam inference...
    python "src\inference\esp32_live_inference.py" --local
) else (
    echo [INFO] Starting ESP32-CAM inference on %ESP32_IP% ...
    python "src\inference\esp32_live_inference.py" --ip %ESP32_IP%
)

echo.
if errorlevel 1 (
    echo [ERROR] The model launcher stopped with an error.
) else (
    echo [INFO] Inference session ended.
)

echo.
pause
