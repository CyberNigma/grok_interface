# Grok Chat Interface

This project provides a Python-based interface to interact with the Grok chat service (hosted at `https://www.grok.com`) via a command-line client. It uses asynchronous programming and Selenium WebDriver to connect to the web-based chat, send messages, and receive responses in real-time.

## Files

### `grok_chat.py`
A command-line client script for chatting with Grok.

- **Purpose**: Provides a simple interface for users to send messages to Grok and display responses.
- **Features**:
  - Connects to Grok using the `GrokInterface` class.
  - Takes user input in a loop, sending messages and printing responses.
  - Supports exiting with "exit" or "quit" commands.
  - Adds extra newlines to responses for readability.
- **Dependencies**: `asyncio`, `sys`, `grok_interface` (see `grok_interface.py`).
- **Usage**: Run directly with `python grok_chat.py`.

### `grok_interface.py`
The core implementation of the `GrokInterface` class for interacting with the Grok web chat.

- **Purpose**: Handles the connection, message sending, and response retrieval from the Grok website using Selenium.
- **Features**:
  - Manages authentication cookies stored in `grok_cookies.json`.
  - Supports manual CAPTCHA solving in headed browser mode.
  - Sends messages via the chat input field.
  - Asynchronously yields responses (paragraphs, lists, code blocks) as they load.
  - Formats code blocks with triple backticks and language identifiers.
  - Closes the browser connection cleanly.
- **Dependencies**: `selenium`, `webdriver_manager`, `asyncio`, `json`, `os`, `logging`, `time`, `sys`.
- **Usage**: Imported by `grok_chat.py` as the backend interface.

## Prerequisites

- Python 3.7+
- Chrome browser installed (for Selenium WebDriver)

## Setup

1. **Clone the repository**:
   ```
   git clone https://github.com/yourusername/grok-chat-interface.git
   cd grok-chat-interface
   ```


2. **Install dependencies**:
   ```
   pip install selenium webdriver_manager
   ```


3. **Prepare cookies**:
- Manually log in to `https://www.grok.com` in Chrome.
- Export the cookies (`cf_clearance`, `sso`, `sso-rw`) to a file named `grok_cookies.json` in the project directory. Example format:
  ```
  [
      {"name": "cf_clearance", "value": "...", "domain": ".grok.com"},
      {"name": "sso", "value": "...", "domain": ".grok.com"},
      {"name": "sso-rw", "value": "...", "domain": ".grok.com"}
  ]
  ```

## Running the Client

1. Start the chat client:
   ```
   python grok_chat.py
   ```


2. Follow the prompts:
- If a CAPTCHA appears, solve it manually in the opened browser and press Enter in the terminal.
- Type your message and press Enter to send.
- Responses will be displayed as they arrive.
- Type "exit" or "quit" to stop.

## Notes

- The Selenium WebDriver runs in headed mode by default to allow CAPTCHA solving.
- Ensure `grok_cookies.json` contains valid, up-to-date cookies for authentication.
- The project assumes the Grok chat interface structure as of the latest update; changes to the website may require script adjustments.

## License

This project is licensed under the 3-Clause BSD License. See the `LICENSE` file for details.
