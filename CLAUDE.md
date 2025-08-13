# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FriendAI is a WeChat ecosystem social relationship management system that helps users efficiently manage and maintain important social relationships through AI-powered user profiling and natural language search capabilities.

### System Components
- **WeiXinKeFu/**: Python FastAPI backend service for user profile analysis and message processing
- **weixi_minimo/**: WeChat Mini Program frontend for contact management and AI search

## High-Level Architecture

### Data Flow
```
WeChat Message → Backend API → AI Analysis → User Profile → Database Storage → Frontend Display
```

### Key Integration Points
1. **WeChat Integration**: Enterprise WeChat and WeChat Customer Service platforms send messages to backend callbacks
2. **AI Processing**: Messages are analyzed using Qwen API to extract structured user profiles
3. **Data Isolation**: Each WeChat user has isolated data storage (separate database tables)
4. **Frontend API**: RESTful API with token authentication for mini program access
5. **Real-time Sync**: Frontend polls for updates and caches data locally

## Development Commands

### Backend Development (WeiXinKeFu)

```bash
# Start development server
cd WeiXinKeFu
python run.py  # Uses uvicorn with auto-reload

# Or use uvicorn directly
uvicorn src.core.main:app --reload --host 0.0.0.0 --port 8000

# Run API tests
python tests/test_api.py

# Database management (development)
python scripts/db_viewer_sqlite.py  # View SQLite database
python scripts/db_viewer_pg.py      # View PostgreSQL database

# Check user data
python scripts/check_users.py

# Add test data
python test-scripts/add_test_data.py
```

### Frontend Development (weixi_minimo)

```bash
# Open WeChat Developer Tools and import the weixi_minimo directory
# Configure server domain: http://localhost:8000 (development) or https://weixin.dataelem.com (production)

# Build npm dependencies (required first time)
# In WeChat Developer Tools: Menu → Tools → Build npm

# Compile and preview
# Use Ctrl+B (Win) / Cmd+B (Mac) or click Compile button

# Clear cache if needed
# Settings page → "Clear Local Data" button
```

### Environment Setup

```bash
# Backend dependencies
pip install -r WeiXinKeFu/requirements.txt

# Configure environment variables
cp WeiXinKeFu/.env.example WeiXinKeFu/.env  # Edit with your credentials
```

## Architecture Patterns

### Backend Architecture (WeiXinKeFu)

**Layered Design**:
- `core/` - API layer (FastAPI endpoints, authentication, CORS)
- `services/` - Business logic (AI analysis, media processing, WeChat client)
- `handlers/` - Message processing pipeline (classification, formatting, processing)
- `database/` - Data persistence (SQLite/PostgreSQL with user isolation)
- `config/` - Configuration management

**Key Design Decisions**:
- Each WeChat user gets isolated data tables (`user_{openid}` format)
- Dual database support via `DB_TYPE` environment variable
- Message processing pipeline: Decrypt → Classify → Extract → Analyze → Store
- Token-based authentication with Base64 encoding (JWT recommended for production)

### Frontend Architecture (weixi_minimo)

**Core Patterns**:
- **Singleton Managers**: `authManager`, `dataManager`, `apiClient` for centralized state
- **Route Guards**: Auto-redirect to login for protected pages via `app.js` interceptors
- **Caching Strategy**: 5-minute local cache with automatic expiration checks
- **Mock Mode**: Offline development support with simulated data
- **Event System**: Listener pattern for cross-component communication

**Data Flow**:
1. Authentication: WeChat login → Backend API → JWT token → Local storage
2. Data Fetching: Check cache → API call with token → Update cache → Render
3. Error Handling: 3x retry with exponential backoff → Fallback to cache/mock data

## Critical Configuration

### Backend Environment Variables (.env)
```bash
# Required for WeChat integration
WEWORK_CORP_ID=your_corp_id
WEWORK_SECRET=your_secret
WEWORK_TOKEN=your_token
WEWORK_AES_KEY=your_aes_key

# Required for AI analysis
QWEN_API_KEY=your_qwen_api_key

# Database (choose one)
DATABASE_PATH=user_profiles.db  # SQLite
DATABASE_URL=postgresql://...   # PostgreSQL

# WeChat Mini Program
WECHAT_MINI_APPID=wx50fc05960f4152a6
WECHAT_MINI_SECRET=your_secret
```

### Frontend Configuration
- Server domain whitelist in WeChat platform
- TDesign components require npm build
- Development mode disables domain validation

## API Endpoints

### Authentication
- `POST /api/login` - WeChat login with code or test user ID

### Contacts Management
- `GET /api/contacts` - List with pagination and search
- `POST /api/contacts` - Create new contact
- `GET /api/contacts/{id}` - Get contact details
- `PUT /api/contacts/{id}` - Update contact
- `DELETE /api/contacts/{id}` - Delete contact

### Search & Analytics
- `POST /api/search` - AI-powered semantic search
- `GET /api/stats` - User statistics

### WeChat Callbacks
- `POST /wechat_callback` - WeChat message webhook
- `GET /wechat_callback` - Webhook verification

## Database Schema

### User Profiles Table (user_{openid})
- `id`: Primary key
- `name`: Contact name (required)
- `wechat_id`: WeChat ID
- `phone`: Phone number
- `tags`: JSON array of labels
- `basic_info`: JSON object with demographics
- `recent_activities`: JSON array of activities
- `raw_messages`: Original message history
- `created_at/updated_at`: Timestamps

### Binding Info Table
- Maps WeChat user IDs to external contact IDs
- Enables cross-platform user matching

## Testing Strategy

### Backend Testing
- Use `test_api.py` for API endpoint validation
- Test accounts: `test_user_001`, `dev_user_001`
- Mock mode for offline testing

### Frontend Testing
- Development environment auto-uses `dev_user_001`
- Mock mode with 5 pre-configured test contacts
- Settings page provides all login methods for testing

## Common Development Tasks

### Adding New Message Types
1. Update classification in `handlers/message_classifier.py`
2. Add processing logic in `handlers/message_handler.py`
3. Implement text extraction in `handlers/message_formatter.py`
4. Update AI prompts in `services/ai_service.py` if needed

### Modifying API Endpoints
1. Add/update endpoint in `core/main.py`
2. Update frontend `api-client.js` with new methods
3. Add business logic in `data-manager.js`
4. Update `constants.js` with any new configurations

### Adding Frontend Pages
1. Create page folder in `pages/`
2. Add `.js`, `.json`, `.wxml`, `.wxss` files
3. Register in `app.json` pages array
4. Add to protected pages in `app.js` if authentication required

## Important Notes

### Security Considerations
- Token authentication is simplified (Base64), upgrade to JWT for production
- Each user's data is completely isolated in separate tables
- WeChat messages are encrypted in transit
- Sensitive information should be masked in AI responses

### Performance Optimization
- Frontend implements 5-minute cache to reduce API calls
- Backend uses connection pooling for database
- AI calls are rate-limited by Qwen API quotas
- Media processing has timeout protection

### Error Handling
- Backend: Comprehensive try-catch with detailed logging
- Frontend: 3x retry with exponential backoff
- Fallback: Cache data → Mock data → Error message
- User feedback: Toast notifications for all operations

### Deployment Considerations
- Production requires valid HTTPS certificates
- WeChat platform domain whitelist configuration
- Database migration tools for SQLite → PostgreSQL
- Environment-specific configuration files

## Debugging Tips

### Backend Debugging
- Check uvicorn console for request logs
- Database viewers for data inspection
- Test API endpoints with `test_api.py`
- Verify WeChat signature in callbacks

### Frontend Debugging
- WeChat Developer Tools console for logs
- Network panel for API request inspection
- Storage panel for cache inspection
- Settings page for authentication status

### Common Issues
- **Login fails**: Check backend running, verify credentials
- **No data displayed**: Validate token, check API response format
- **WeChat callback errors**: Verify encryption keys, check signature
- **AI analysis fails**: Confirm Qwen API key and quotas
- **TDesign components missing**: Run "Build npm" in developer tools