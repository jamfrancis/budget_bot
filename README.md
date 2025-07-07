Overview

  bal.ai is a Django-based personal finance web application that combines intelligent account tracking,
  transaction monitoring, and AI-powered financial advice through Claude integration. The app features Plaid
  banking connectivity for automatic transaction sync, real-time chat functionality via WebSockets, and a modern
   interface built with Tailwind CSS.

  The application integrates Plaid API for secure connection to financial institutions, automatically importing
  account balances and transactions. The AI chat system uses Anthropic's Claude 3.5 Haiku to provide contextual
  financial advice based on user's actual financial data. Real-time communication is handled through Django
  Channels with WebSocket support, creating an instant messaging experience for financial consultations.

  As a software engineer, I developed this application to master full-stack web development with modern Python
  frameworks, explore real-time communication protocols, and understand financial API integration and AI service
   orchestration.

  To start the application:
  1. Navigate to project directory: cd budget_bot
  2. Start server: ./start_server.sh
  3. Open browser to: http://127.0.0.1:8083/

  http://youtube.link.goes.here

  Web Pages

  Chat Interface (Homepage - /)
  Main interface featuring a conversation sidebar and real-time messaging area. Users can create conversations,
  interact with bal.ai through natural language, and access clickable example questions. Includes real-time
  typing indicators and auto-scrolling that positions long responses for optimal readability.

  Dashboard (/dashboard/)
  Financial overview displaying connected accounts, recent transactions, and management tools. Dynamically
  calculates balances, shows account status through color-coded badges, and provides collapsible sections for
  adding accounts/transactions. Features Plaid integration, manual account entry, and bulk management
  operations.

  Navigation flows seamlessly between AI-driven financial guidance and detailed data management, with responsive
   design across both interfaces.

  Development Environment

  Developed using Visual Studio Code on macOS with Django's development server for testing. Built in Python 3.12
   using Django 5.2.3 web framework, Django Channels 4.2.2 for WebSockets, and Daphne ASGI server. Frontend uses
   Django templates with Tailwind CSS and vanilla JavaScript. Key integrations include Anthropic's Python SDK
  for Claude AI, Plaid's Python client for banking, Django REST Framework for APIs, and Celery for background
  tasks.

  Useful Websites

  - https://docs.djangoproject.com/en/5.2/
  - https://channels.readthedocs.io/en/stable/
  - https://docs.anthropic.com/en/api/getting-started
  - https://plaid.com/docs/api/
  - https://www.django-rest-framework.org/
  - https://tailwindcss.com/docs

  Future Work

  - Implement data visualization with interactive charts for spending analysis
  - Add multi-user authentication system with secure registration
  - Create advanced transaction categorization with machine learning