# File Vault Frontend

This is the React frontend for the File Vault system.

## Features

- User registration and authentication
- Clean, modern UI with responsive design
- JWT token management with automatic refresh
- Form validation and error handling

## Getting Started

### Development

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The app will be available at http://localhost:3000

### Docker

The frontend is configured to run with Docker Compose. See the main project README for instructions.

## Project Structure

```
src/
├── components/     # React components
│   ├── Login.js
│   ├── Register.js
│   └── Dashboard.js
├── services/       # API services
│   └── api.js
├── utils/          # Utility functions
│   └── auth.js
├── App.js          # Main app component
├── index.js        # Entry point
└── index.css       # Global styles
```

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App 