# Content Inspiration

A Streamlit-powered web application that intelligently scrapes and summarizes articles from the Google AI Blog, complete with image downloads and AI-generated summaries for enhanced content discovery.

## 🚀 Features

- **Smart Article Collection**: Automatically scrapes article links from Google AI Blog homepage
- **Content Processing**: Downloads and processes article content with structured storage
- **Image Management**: Retrieves and organizes all images referenced in articles
- **AI-Powered Summaries**: Generates concise paragraph summaries using local Ollama models
- **Interactive Web Interface**: Browse, search, and filter content through an intuitive Streamlit dashboard
- **Configurable Setup**: Easy configuration through YAML files

## 📋 Prerequisites

- **Python**: Version 3.10 or newer
- **Ollama**: A running [Ollama](https://ollama.ai/) instance with your preferred model
- **Environment Variables**: User agent configuration for web scraping

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AdemCE-eng/Content_Inspiration.git
   cd content_inspiration
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
   ```
   
   > **Note**: Replace with your actual browser's user agent string. You can find this by searching "what is my user agent" in your browser.

5. **Configure Ollama**
   
   The application automatically launches `ollama serve` when summaries are generated and terminates the process when summarization completes. On Windows, any lingering child processes are forcibly killed.   
   Make sure the `ollama` CLI is installed and pull the required model:
   ```bash
   ollama pull mistral  # or your preferred model
   ```

## 🚀 Usage

### Starting the Application

**Option 1: Command Line**
```bash
streamlit run main.py
```

**Option 2: Windows Batch File**
```bash
run_app.bat
```
This automatically activates the virtual environment before launching Streamlit.

### Using the Application

1. **Launch**: Open your browser to the Streamlit interface (typically `http://localhost:8501`)

2. **Content Pipeline**: Use the sidebar to trigger the four-step scraping process:
   - 📄 **Step 1**: Scrape article links from Google AI Blog
   - 💾 **Step 2**: Download article content and metadata
   - 🖼️ **Step 3**: Download and organize referenced images
   - 🤖 **Step 4**: Generate AI summaries for each paragraph

3. **Browse Content**: Explore articles through the interactive interface with:
   - Search functionality
   - Content filtering options
   - Image galleries
   - Summary previews

## 📁 Project Structure

```
content-inspiration/
├── config/config.yaml      # Application configuration
├── data/
│   ├── processed/          # Processed article storage
│   └── raw/                # Raw input links for scraping
├── images/                 # Downloaded article images
├── logs/                   # Application logs
├── src/
│   ├── utils/              # Utility modules
│   └── websites/           # Scraping modules and main app logic
├── main.py                 # Main Streamlit application
└── requirements.txt        # Python dependencies
```

## ⚙️ Configuration

The application uses `config/config.yaml` for configuration. Key settings include:

- **Data Storage**: Paths for processed articles, images and logs
- **Sources**: URLs to scrape (e.g. `google_ai_blog`)
- **Request Settings**: Timeout, retries and rate limiting
- **Ollama Model**: Base URL, model name and timeout
- **UI Settings**: Configure number of articles per page

By default, the configuration sets `mistral` as the LLM model. If you want to
use another model, open `config/config.yaml` and change the value of
`ollama.model` to your preferred model name.

## 🔧 Troubleshooting

**Common Issues:**

- **Ollama Connection Error**: The app tries to start `ollama serve` automatically. Ensure the `ollama` CLI is installed and accessible.
- **User Agent Issues**: Verify your `.env` file contains a valid user agent string
- **Permission Errors**: Check write permissions for `data/` and `images/` directories
- **Missing Dependencies**: Run `pip install -r requirements.txt` to ensure all packages are installed

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google AI Blog for providing excellent content
- Ollama team for the local AI model infrastructure
- Streamlit for the intuitive web framework

---