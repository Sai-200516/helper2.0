Helper2.0
Helper2.0 is a chatbot application that integrates a FastAPI-based backend with a PyQt5-based desktop client. The server connects to the Gemini AI API for natural language processing and uses MongoDB for managing user registrations and trial activations. The client provides a user-friendly interface with features like OCR-based text extraction, clipboard integration, and system tray functionality for seamless interaction.
Table of Contents

Features
Architecture
Installation
Server Setup
Client Setup


Usage
Server
Client


API Endpoints
Environment Variables
Contributing
License

Features

Server (server.py):

Built with FastAPI for high-performance API endpoints.
Integrates with Gemini AI API for chatbot functionality.
MongoDB for managing registration numbers, activations, and trial usage.
Supports trial and premium user tiers with command limits and expiry checks.
Secure API key and admin authentication.
Response caching for improved performance.


Client (client.py):

PyQt5-based GUI with a compact, always-on-top chat window.
OCR functionality to extract text from screen captures using Tesseract.
Clipboard integration for copying/pasting questions and responses.
System tray icon for easy access and hotkey support (Ctrl+Shift+ or Alt+Shift+G).
Platform-specific optimizations for Windows and macOS (e.g., window cloaking, topmost behavior).
Trial and premium activation support with a user-friendly dialog.
Stealth Features: The application is designed to remain hidden during screen sharing, does not appear in the taskbar, Task Manager, or system event logs, ensuring discreet operation.



Architecture

Server: A FastAPI application that handles user authentication, trial/premium activations, and chatbot queries. It connects to MongoDB for persistent storage and the Gemini API for generating responses.
Client: A PyQt5 desktop application that communicates with the server via HTTP requests. It provides a GUI for users to interact with the chatbot, capture screen regions for OCR, and manage activation.

Installation
Server Setup

Clone the Repository:
git clone https://github.com/Sai-200516/helper2.0.git
cd helper2.0


Install Dependencies:Ensure Python 3.8+ is installed, then install the required packages:
pip install fastapi uvicorn pymongo google-generativeai python-dotenv


Set Up Environment Variables:Create a .env file in the project root with the following:
GEMINI_API_KEY=your_gemini_api_key
API_KEY_VALUE=your_api_key
HELPER_ADMIN_API_KEY=your_admin_api_key
MONGO_URI=your_mongodb_uri
gmail=your_support_email


Run the Server:
python server.py

The server will start on http://localhost:8000 (or your configured host/port).


Client Setup

Install Dependencies:Install the required Python packages:
pip install requests pystray pillow pynput pyperclip pytesseract opencv-python PyQt5 tenacity

For OCR functionality, install Tesseract OCR:

Windows: Download and install from Tesseract at UB Mannheim. Add Tesseract to your system PATH.
macOS: Install via Homebrew:brew install tesseract


Linux: Install via package manager:sudo apt-get install tesseract-ocr




Set Up Environment Variables:Add the following to your .env file (or update the existing one):
HELPER_SERVER_URL=your_server_url
HELPER_API_KEY=your_api_key


Run the Client:
python client.py



Usage
Server

The server exposes several API endpoints for managing registrations and handling chatbot queries.
Ensure MongoDB is running and accessible via the provided MONGO_URI.
The server supports trial activations (limited to 20 commands, expiring on May 21, 2025) and premium activations.

Client

On first launch, the client prompts for activation (trial or premium).
Trial Activation: Uses the code Helper2.0_Trail for 15 commands.
Premium Activation: Requires a valid registration number provided by the support team.
Use the GUI to:
Type queries directly or copy them from the clipboard.
Capture screen regions for OCR to extract text.
Copy or paste responses using dedicated buttons.
Minimize to the system tray or toggle visibility with hotkeys.



API Endpoints

POST /admin/add_reg_no: Add a new registration number (admin only).
Headers: X-Admin-API-Key
Body: {"reg_no": "string", "is_active": boolean}


POST /trial_activate: Activate trial mode for a MAC address.
Body: {"activation_code": "Helper2.0_Trail", "mac_address": "string"}


POST /activate: Activate a premium registration.
Headers: X-API-Key
Body: {"reg_no": "string", "mac_address": "string"}


POST /chat: Send a chatbot query.
Headers: X-API-Key, X-Reg-No, X-MAC-Address
Body: {"query": "string"}



Environment Variables



Variable
Description
Example Value



GEMINI_API_KEY
Gemini AI API key
your_gemini_api_key


API_KEY_VALUE
API key for client authentication
your_api_key


HELPER_ADMIN_API_KEY
Admin API key for restricted endpoints
your_admin_api_key


MONGO_URI
MongoDB connection URI
mongodb://localhost:27017


gmail
Support email for premium subscriptions
support@example.com


HELPER_SERVER_URL
Server URL for client requests
http://localhost:8000


HELPER_API_KEY
API key for client-server communication
your_api_key


Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.
Create a new branch (git checkout -b feature/your-feature).
Commit your changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a pull request.

Please ensure your code follows PEP 8 style guidelines and includes appropriate tests.
License
This project is licensed under the MIT License. See the LICENSE file for details.
