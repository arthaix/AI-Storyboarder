@echo off
echo Starting AI Storyboarder server...

:: Check if virtual environment exists
if exist venv\Scripts\activate (
    echo Activating virtual environment...
    call venv\Scripts\activate
)

:: Ensure OpenAI API key is set (Change "your_openai_api_key_here" if needed)
if not defined OPENAI_API_KEY set OPENAI_API_KEY=your_openai_api_key_here

:: Run Flask server
python app.py
pause
