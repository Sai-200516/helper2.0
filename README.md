# Helper2.0

Helper2.0 is a chatbot application that integrates a FastAPI-based backend with a PyQt5-based desktop client. The server connects to the Gemini AI API for natural language processing and uses MongoDB for managing user registrations and trial activations. The client provides a user-friendly interface with features like OCR-based text extraction, clipboard integration, and system tray functionality for seamless interaction. The application is designed to operate discreetly, remaining hidden during screen sharing and not appearing in the taskbar, Task Manager, or system event logs.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Libraries Used](#libraries-used)
- [Installation](#installation)
  - [Server Setup](#server-setup)
  - [Client Setup](#client-setup)
- [Testing](#testing)
- [Usage](#usage)
  - [Server](#server)
  - [Client](#client)
- [API Endpoints](#api-endpoints)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [License](#license)

## Features
- **Server (server.py):**
  - Built with FastAPI for high-performance API endpoints.
  - Integrates with Gemini AI API for chatbot functionality.
  - MongoDB for managing registration numbers, activations, and trial usage.
  - Supports trial and premium user tiers with command limits and expiry checks.
  - Secure API key and admin authentication.
  - Response caching for improved performance.

- **Client (client.py):**
  - PyQt5-based GUI with a compact, always-on-top chat window.
  - OCR functionality to extract text from screen captures using Tesseract.
  - Clipboard integration for copying/pasting questions and responses.
  - System tray icon for easy access and hotkey support (Ctrl+Shift+<random_letter> or Alt+Shift+G).
  - Platform-specific optimizations for Windows and macOS (e.g., window cloaking, topmost behavior).
  - Trial and premium activation support with a user-friendly dialog.
  - **Stealth Features**: The application operates discreetly, remaining hidden during screen sharing, and does not appear in the taskbar, Task Manager, or system event logs, ensuring minimal visibility on the system.

## Architecture
- **Server**: A FastAPI application that handles user authentication, trial/premium activations, and chatbot queries. It connects to MongoDB for persistent storage and the Gemini API for generating responses.
- **Client**: A PyQt5 desktop application that communicates with the server via HTTP requests. It provides a GUI for users to interact with the chatbot, capture screen regions for OCR, and manage activation.

## Libraries Used
The following libraries are used in the Helper2.0 application:

- **Server (server.py)**:
  - `fastapi`: For building the API server.
  - `uvicorn`: ASGI server implementation for running the FastAPI application.
  - `pymongo`: For interacting with MongoDB.
  - `google-generativeai`: For integrating with the Gemini AI API.
  - `python-dotenv`: For loading environment variables from a `.env` file.
  - `pydantic`: For data validation and settings management.
  - `logging`: For server-side logging.
  - `datetime`, `pytz`: For handling dates and timezones.
  - `os`, `time`: For system operations and timing.

- **Client (client.py)**:
  - `PyQt5`: For building the graphical user interface.
  - `requests`: For making HTTP requests to the server.
  - `pystray`: For system tray integration.
  - `pillow` (PIL): For image processing in OCR.
  - `pynput`: For keyboard hotkey support and simulated typing.
  - `pyperclip`: For clipboard operations.
  - `pytesseract`: For OCR text extraction.
  - `opencv-python` (cv2): For image preprocessing in OCR.
  - `tenacity`: For retrying failed API requests.
  - `uuid`, `hashlib`: For generating and hashing MAC addresses.
  - `json`, `os`, `sys`, `threading`, `time`, `random`, `string`: For system operations, configuration, and randomization.
  - `ctypes`: For Windows-specific system calls (e.g., window cloaking).
  - `AppKit`, `Foundation`, `objc` (macOS only): For macOS-specific window behavior.

## Installation

### Server Setup
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Sai-200516/helper2.0.git
   cd helper2.0
   ```

2. **Install Dependencies**:
   Ensure Python 3.8+ is installed, then install the required packages:
   ```bash
   pip install fastapi uvicorn pymongo google-generativeai python-dotenv
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the project root with the following:
   ```plaintext
   GEMINI_API_KEY=your_gemini_api_key
   API_KEY_VALUE=your_api_key
   HELPER_ADMIN_API_KEY=your_admin_api_key
   MONGO_URI=your_mongodb_uri
   gmail=your_support_email
   ```

4. **Run the Server**:
   ```bash
   python server.py
   ```
   The server will start on `http://localhost:8000` (or your configured host/port).

### Client Setup
1. **Install Dependencies**:
   Install the required Python packages:
   ```bash
   pip install requests pystray pillow pynput pyperclip pytesseract opencv-python PyQt5 tenacity
   ```
   For OCR functionality, install Tesseract OCR:
   - **Windows**: Download and install from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). Add Tesseract to your system PATH.
   - **macOS**: Install via Homebrew:
     ```bash
     brew install tesseract
     ```
   - **Linux**: Install via package manager:
     ```bash
     sudo apt-get install tesseract-ocr
     ```

2. **Set Up Environment Variables**:
   Add the following to your `.env` file (or update the existing one):
   ```plaintext
   HELPER_SERVER_URL=your_server_url
   HELPER_API_KEY=your_api_key
   ```

3. **Run the Client**:
   ```bash
   python client.py
   ```

## Testing
To test the application without setting up the Python environment, you can download the precompiled executable:
- **Download**: Get the `helper2.0.exe` file from the [Releases](https://github.com/Sai-200516/helper2.0/releases) section of the GitHub repository.
- **Run**: Double-click the `helper2.0.exe` file on a Windows system to launch the client application.
- **Stealth Features**: The executable is designed to operate discreetly, remaining hidden during screen sharing and not appearing in the taskbar, Task Manager, or system event logs.
- **Note**: Ensure you have a working server instance (configured with the correct environment variables) for the client to communicate with. For full functionality, including OCR, Tesseract must be installed and accessible.

## Usage

### Server
- The server exposes several API endpoints for managing registrations and handling chatbot queries.
- Ensure MongoDB is running and accessible via the provided `MONGO_URI`.
- The server supports trial activations (limited to 20 commands, expiring on May 21, 2025) and premium activations.

### Client
- On first launch, the client prompts for activation (trial or premium).
- **Trial Activation**: Uses the code `Helper2.0_Trail` for 15 commands.
- **Premium Activation**: Requires a valid registration number provided by the support team.
- Use the GUI to:
  - Type queries directly or copy them from the clipboard.
  - Capture screen regions for OCR to extract text.
  - Copy or paste responses using dedicated buttons.
  - Minimize to the system tray or toggle visibility with hotkeys.

## API Endpoints
- **POST /admin/add_reg_no**: Add a new registration number (admin only).
  - Headers: `X-Admin-API-Key`
  - Body: `{"reg_no": "string", "is_active": boolean}`
- **POST /trial_activate**: Activate trial mode for a MAC address.
  - Body: `{"activation_code": "Helper2.0_Trail", "mac_address": "string"}`
- **POST /activate**: Activate a premium registration.
  - Headers: `X-API-Key`
  - Body: `{"reg_no": "string", "mac_address": "string"}`
- **POST /chat**: Send a chatbot query.
  - Headers: `X-API-Key`, `X-Reg-No`, `X-MAC-Address`
  - Body: `{"query": "string"}`

## Environment Variables
| Variable              | Description                              | Example Value                     |
|-----------------------|------------------------------------------|-----------------------------------|
| `GEMINI_API_KEY`      | Gemini AI API key                        | `your_gemini_api_key`            |
| `API_KEY_VALUE`       | API key for client authentication        | `your_api_key`                   |
| `HELPER_ADMIN_API_KEY`| Admin API key for restricted endpoints    | `your_admin_api_key`             |
| `MONGO_URI`           | MongoDB connection URI                   | `mongodb://localhost:27017`      |
| `gmail`               | Support email for premium subscriptions   | `support@example.com`            |
| `HELPER_SERVER_URL`   | Server URL for client requests           | `http://localhost:8000`          |
| `HELPER_API_KEY`      | API key for client-server communication  | `your_api_key`                   |

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Please ensure your code follows PEP 8 style guidelines and includes appropriate tests.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
