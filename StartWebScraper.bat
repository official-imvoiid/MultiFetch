@echo off
title CLI-WEBSCRAPER
echo CLI-WEBSCRAPER
echo.
echo WARNING:
echo 1.Always use for private use only.
echo 2.Respect fair use and these platforms TOS.
echo 3.Developer is not responsible for your actions.
echo 4.Maximum tested for 1500 images per topic.
echo 5.More than 1500 images scraping may be possible but not tested.
echo 6.Maxium of 170 Gif scraping tested 
echo 7.More than 170 Gif scraping may be possible but not tested.
echo.
echo Checking Python installation...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher and try again.
    echo.
    pause
    exit /b 1
)

:: Get Python version and check if it's 3.8 or higher
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

:: Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

:: Check if version is 3.8 or higher
if %MAJOR% LSS 3 (
    echo ERROR: Python version %PYTHON_VERSION% is too old.
    echo This application requires Python 3.8 or higher.
    echo Please upgrade your Python installation.
    echo.
    pause
    exit /b 1
)

if %MAJOR% EQU 3 if %MINOR% LSS 8 (
    echo ERROR: Python version %PYTHON_VERSION% is too old.
    echo This application requires Python 3.8 or higher.
    echo Please upgrade your Python installation.
    echo.
    pause
    exit /b 1
)

echo Python version check passed.
echo.
echo Press any key to continue...
pause > nul

:menu
cls
echo CLI-WEBSCRAPER
echo.
echo Select an option:
echo 0. Image Converter
echo 1. Image Upscaler
echo 2. Static Page Scraper
echo 3. Deviantart Scraper
echo 4. Web GIF Scraper
echo 5. Pintrest Scraper
echo 6. Google Images Scraper
echo 7. Pixiv Scraper
echo 8. Exit
echo.
set /p choice=Enter your choice: 

if "%choice%"=="0" goto converter
if "%choice%"=="1" goto upscaler
if "%choice%"=="2" goto staticpage
if "%choice%"=="3" goto deviantart
if "%choice%"=="4" goto webgif
if "%choice%"=="5" goto pintrest
if "%choice%"=="6" goto googleimages
if "%choice%"=="7" goto pixiv
if "%choice%"=="8" goto end

echo Invalid choice, please try again.
pause
goto menu

:converter
cls
python Modules\Image_converter.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:upscaler
cls
python Modules\Image_upscaler.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:staticpage
cls
python Modules\Staticpage_scraper.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:deviantart
cls
python Modules\Deviantart_scraper.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:webgif
cls
python Modules\WebGifScraper.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:pintrest
cls
python Modules\Pintrest_scraper.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:googleimages
cls
python Modules\GoogleImagesScraper.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:pixiv
cls
python Modules\PixivScraper.py
echo.
echo Press any key to return to the menu...
pause > nul
goto menu

:end
echo Thank you for using CLI-WEBSCRAPER.
pause