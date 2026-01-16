# 🌐 Integral Philosophy Web Components

Web interface and API components for academic publishing system.

## 📦 What's Included

- **🎨 Web Interface** - Modern responsive UI
- **🔌 REST API** - RESTful API endpoints  
- **📱 Templates** - HTML templates and static assets
- **🎭 Real-time** - WebSocket processing updates
- **📊 Dashboard** - Processing status and metrics

## 🚀 Quick Start

\`\`\`bash
# Install
pip install integral-philosophy-web[all]

# Run web interface
integral-web --port 8000

# Run API server
integral-api --port 8001

# Run full stack
integral-web --full-stack
\`\`\`

## 🏗️ Architecture

\`\`\`
📱 Web Frontend → 🔌 API Gateway → 🧠 Core Engine → 📚 Output Formats
       │                    │                    │                 │
  • React UI         • FastAPI          • Content Parsers   • HTML
  • Drag & Drop      • REST Endpoints     • Format Converters  • PDF
  • Live Updates      • GraphQL Query      • Content Validators • EPUB
  • WebSocket         • Background Jobs    • Content Generators • TEI XML
\`\`\`

## 📦 Installation

\`\`\`bash
pip install integral-philosophy-web[all]  # Full installation
pip install integral-philosophy-web[ui]  # Web interface only
pip install integral-philosophy-web[api]  # API only
\`\`\`

## 🎨 Features

### Web Interface
- 📱 **Responsive Design** - Mobile-first UI
- 🎨 **Modern Framework** - React/Vue.js components
- ⚡ **Real-time Updates** - WebSocket integration
- 📊 **Processing Dashboard** - Live status monitoring
- 📁 **File Management** - Drag-and-drop uploads

### API Components
- 🔌 **REST API** - Full CRUD operations
- 📊 **GraphQL Support** - Efficient data queries
- 🔄 **Background Jobs** - Async processing
- 📈 **Rate Limiting** - Built-in protection
- 🔐 **Authentication** - JWT-based security

## 🛠️ Development

\`\`\`bash
# Setup development environment
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run frontend development
npm run dev  # Web interface
npm run build  # Production build

# Run backend development  
uvicorn integral_philosophy_web.api:app --reload
pytest tests/  # Run tests
\`\`\`

## 📚 Documentation

- [API Reference](docs/api.md)
- [UI Components Guide](docs/ui.md) 
- [Development Guide](docs/dev.md)

## 🤝 Contributing

1. Fork repository
2. Feature branch
3. Pull request

## 📄 License

MIT License - see LICENSE file
