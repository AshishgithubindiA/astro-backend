# Astro Backend API

A FastAPI-based backend for an astrology application, providing astrological calculations, profile management, and AI-powered chat functionality.

## Features

- User management with auto-generated UUIDs
- Birth chart calculation using Swiss Ephemeris
- Daily astrological context based on current transits
- AI-powered chat with specialized responses for:
  - Daily astrological vibes
  - Relationship advice
  - Mood check-ins
  - Life purpose & career guidance
- User preferences storage
- Mood tracking

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up environment variables in a `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_API_KEY=your_supabase_api_key
   EPHE_PATH=./ephe  # Path to Swiss Ephemeris data files
   ```
5. Run the server:
   ```
   python -m uvicorn astro_api:app --reload
   ```

## API Endpoints

- **User Management**
  - `POST /users` - Create a new user (UUID auto-generated)
  - `GET /users/{user_id}` - Get user details

- **Astro Profiles**
  - `POST /astro-profiles/generate` - Generate a user's astrological profile
  - `GET /astro-profiles/{user_id}` - Get a user's astrological profile

- **Daily Context**
  - `POST /daily-context/generate` - Generate daily astrological context
  - `GET /daily-context/{user_id}/{date}` - Get a user's daily context for a specific date

- **Chat**
  - `POST /chat/message` - Send a message and get an AI response
  - `GET /chat/history/{user_id}` - Get a user's chat history

- **Preferences**
  - `POST /preferences` - Save user preferences
  - `GET /preferences/{user_id}` - Get a user's preferences

- **Mood Check-in**
  - `POST /mood/check-in` - Log a mood check-in

## Database Schema

The application uses Supabase as a backend database with the following tables:

- `users` - User information including birth data
- `astro_profiles` - Calculated astrological profiles 
- `daily_context` - Daily astrological context
- `chat_history` - Chat messages between users and the AI
- `preferences` - User preferences
- `mood_logs` - User mood check-ins
