# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Note: You must push the results to the remote server at https://github.com/ConstTyrone/FriendAI after completing each task.

## Project Overview

FriendAI is a WeChat ecosystem social relationship management system with AI-powered capabilities:
- **User Profile Analysis**: Extracts structured profiles from WeChat messages using Qwen API
- **Intent Matching System**: AI-enhanced matching engine that connects users with relevant contacts based on intent
- **Natural Language Search**: Semantic search across contacts using natural language queries

### System Components
- **WeiXinKeFu/**: Python FastAPI backend service for message processing and AI analysis
- **weixi_minimo/**: WeChat Mini Program frontend for contact management and AI features
- **Intent System**: Advanced matching engine with vector embeddings and multi-criteria scoring

## High-Level Architecture

### Core Data Flows

#### 1. Message Processing Flow
```
WeChat Message → Backend API → AI Analysis → User Profile → Database Storage → Frontend Display
```

#### 2. Intent Matching Flow
```
User Intent → Vector Embedding → Profile Matching → Score Calculation → Push Notification
```

#### 3. Search Flow
```
Natural Language Query → Semantic Analysis → Vector Search → Ranked Results
```

### Intent Matching System Architecture

The intent matching system (`src/services/intent_matcher.py`) is the core innovation, implementing:

1. **Dual-Trigger Mechanism**:
   - **Intent-to-Profiles**: When a new intent is created, matches against all existing contacts
   - **Profile-to-Intents**: When a contact is updated, matches against all active intents

2. **Hybrid Scoring Algorithm**:
   - **Vector Similarity** (30-40%): Semantic understanding using embeddings
   - **Keyword Matching** (30-40%): Direct text matching for precision
   - **Required Conditions** (25-40%): Hard requirements that must be met
   - **Preferred Conditions** (15-20%): Soft preferences that boost scores

3. **AI Enhancement** (`src/services/vector_service.py`):
   - Qwen API for generating embeddings
   - Semantic similarity calculation using cosine distance
   - AI-powered explanation generation for matches
   - Fallback to rule-based matching when AI unavailable

4. **Data Structure**:
   - **user_intents**: Stores intent definitions with conditions and embeddings
   - **intent_matches**: Records match results with scores and explanations
   - **vector_index**: Optimized storage for fast vector similarity searches
   - **push_history**: Tracks notifications to prevent spam

### Key Integration Points
1. **WeChat Integration**: Enterprise WeChat and WeChat Customer Service message callbacks
2. **AI Processing**: Qwen API for embeddings, profile extraction, and explanation generation
3. **Data Isolation**: Multi-user architecture with separate tables per WeChat user
4. **Frontend API**: RESTful endpoints with authentication for mini program
5. **Real-time Updates**: Polling and push notifications for new matches

## Development Commands

### Backend Development (WeiXinKeFu)

```bash
# Start development server
cd WeiXinKeFu
python run.py  # Uses uvicorn with auto-reload

# Or use uvicorn directly
uvicorn src.core.main:app --reload --host 0.0.0.0 --port 8000

# Test intent matching system
python test_intent_system.py        # Test complete intent system
python test_intent_matching.py      # Test matching logic
python test_ai_matching.py          # Test AI-enhanced matching

# Initialize intent system
python scripts/create_intent_tables.py  # Create database tables
python scripts/add_vector_columns.py    # Add vector columns
python scripts/initialize_vectors.py    # Generate initial embeddings

# Database management
python scripts/db_viewer_sqlite.py  # View SQLite database
python scripts/db_viewer_pg.py      # View PostgreSQL database
python scripts/check_users.py       # Check user data

# Add test data
python test-scripts/add_test_data.py
python test-scripts/test_create_contact.py
python test-scripts/test_user_data.py
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

### Intent Management (Backend API)
- `POST /api/intents` - Create new intent with conditions
- `GET /api/intents` - List user's intents with filters
- `PUT /api/intents/{id}` - Update intent conditions
- `DELETE /api/intents/{id}` - Delete intent
- `POST /api/intents/{id}/toggle` - Activate/pause intent
- `POST /api/intents/{id}/match` - Manually trigger matching

### Match Results
- `GET /api/matches` - Get match results with filters
- `GET /api/matches/{id}` - Get match details
- `PUT /api/matches/{id}/feedback` - Provide match feedback
- `POST /api/matches/batch` - Batch operations on matches

### Search & Analytics
- `POST /api/search` - AI-powered semantic search
- `GET /api/stats` - User statistics
- `GET /api/push/history` - Push notification history
- `PUT /api/push/preferences` - Update push preferences

### WeChat Callbacks
- `POST /wechat_callback` - WeChat message webhook
- `GET /wechat_callback` - Webhook verification

## Database Schema

### User Profiles Table (profiles_{user_id})
- `id`: Primary key
- `profile_name`: Contact name (required)
- `wechat_id`: WeChat ID
- `phone`: Phone number
- `tags`: JSON array of labels
- `basic_info`: JSON object with demographics
- `recent_activities`: JSON array of activities
- `raw_messages`: Original message history
- `embedding`: Vector representation for semantic search
- `created_at/updated_at`: Timestamps

### Intent Tables

#### user_intents
- `id`: Primary key
- `user_id`: WeChat user ID
- `name`: Intent name
- `description`: Natural language description
- `type`: Intent type (business/social/recruitment/resource)
- `conditions`: JSON object with matching criteria
- `embedding`: 768-dim vector for semantic matching
- `threshold`: Matching score threshold (0-1)
- `priority`: Intent priority (1-10)
- `status`: active/paused/expired

#### intent_matches
- `id`: Primary key
- `intent_id`: Foreign key to user_intents
- `profile_id`: Foreign key to profiles table
- `match_score`: Overall match score (0-1)
- `matched_conditions`: JSON array of matched criteria
- `explanation`: AI-generated match explanation
- `user_feedback`: positive/negative/ignored
- `is_pushed`: Whether notification was sent

#### vector_index
- `id`: Composite key (type_entityid)
- `vector_type`: intent/profile
- `entity_id`: ID of intent or profile
- `embedding`: Vector data (BLOB)
- `metadata`: Additional metadata (JSON)

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

### Working with Intent Matching System

#### Creating New Intent Types
1. Define intent structure in database schema
2. Update `IntentMatcher._calculate_match_score()` for custom scoring logic
3. Add condition operators in `_check_condition()` method
4. Update AI prompts in `vector_service.py` for better embeddings

#### Optimizing Match Performance
1. Index frequently queried fields in database
2. Cache vector embeddings in `vector_index` table
3. Use batch operations for multiple matches
4. Implement async processing for large datasets

#### Testing Intent Matching
```python
# Quick test of intent matching
from src.services.intent_matcher import intent_matcher

# Test with specific intent and profiles
matches = intent_matcher.match_intent_with_profiles(
    intent_id=1, 
    user_id="test_user"
)
```

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