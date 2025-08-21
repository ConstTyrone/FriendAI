# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Instructions

- **Git**: Push all changes to https://github.com/ConstTyrone/FriendAI after completing each task
- **Testing**: Use test user ID `wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q` for all tests
- **Documentation**: Refer to `weixin_doc/` folder for WeChat Customer Service documentation
- **Theme**: Deep dark mode support implemented with ThemeManager - use `themeManager` singleton for all theme operations
- **Voice**: Advanced voice input with real-time recognition and AI parsing for contact forms
- **Intent System**: Core AI-powered matching engine is the primary innovation feature

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

### Quick Start

```bash
# Backend setup
cd WeiXinKeFu
pip install -r requirements.txt
cp .env.example .env                    # Configure your credentials
python run.py                            # Start server on port 8000

# Frontend setup  
# 1. Open WeChat Developer Tools
# 2. Import weixi_minimo/ directory
# 3. Tools → Build npm (first time only)
# 4. Compile (Ctrl+B/Cmd+B)
```

### Backend Commands

```bash
# Core services (WeiXinKeFu directory)
cd WeiXinKeFu
python run.py                            # Start FastAPI server with auto-reload
uvicorn src.core.main:app --reload --host 0.0.0.0 --port 8000  # Alternative start

# Intent system testing
python tests/integration/test_intent_system.py             # Full intent system test
python tests/integration/test_intent_matching.py           # Test matching logic
python tests/integration/test_ai_matching.py               # Test AI-enhanced matching
python tests/integration/test_hybrid_matching.py           # Test hybrid matching
python tests/integration/test_integrated_system.py         # Integration tests

# Database operations
python scripts/create_intent_tables.py   # Initialize intent tables
python scripts/add_vector_columns.py     # Add vector columns to existing tables
python scripts/initialize_vectors.py     # Generate embeddings for existing data
python scripts/db_viewer_sqlite.py       # Interactive SQLite viewer
python scripts/db_viewer_pg.py           # Interactive PostgreSQL viewer
python scripts/check_users.py            # Check user data integrity
python scripts/migrate_add_tags.py       # Migrate tags column

# Test data management
python test-scripts/add_test_data.py     # Add sample contacts
python test-scripts/test_create_contact.py # Test contact creation
python test-scripts/test_user_data.py    # Verify user data
python test-scripts/reset_test_data.py   # Reset test environment

# API testing
python tests/test_api.py                 # Full API test suite
python tests/integration/test_api_simple.py              # Simple API tests
python tests/integration/test_notification_api.py        # Notification system tests

# Performance optimization
python optimize_prompts.py               # Optimize AI prompts
python ab_testing_framework.py           # A/B testing for matching algorithms
python generate_embeddings.py            # Batch generate embeddings
```

### Frontend Commands (WeChat Mini Program)

```bash
# In WeChat Developer Tools:
# 1. Tools → Build npm                   # Required for TDesign components
# 2. Compile (Ctrl+B/Cmd+B)              # Build project
# 3. Preview                             # Test on mobile device  
# 4. Upload                              # Deploy to production

# Theme development:
# - Toggle theme in Settings page        # Test dark/light mode switching
# - Check system theme compatibility     # Auto-follow system settings
# - Test navigation bar color updates    # Verify theme transitions

# Voice input testing:
# - Use voice button in contact forms    # Test real-time recognition
# - Test AI field parsing                # Verify intelligent form filling
# - Check recording state management     # Test press-and-hold vs tap modes

# Debug commands (in Settings page):
# - "Clear Local Data"                   # Clear cache and storage
# - "View Storage Info"                  # Check cache usage
# - Switch login modes                   # Test different auth methods
# - "Theme Settings"                     # Manual theme override
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
- **Singleton Managers**: `authManager`, `dataManager`, `apiClient`, `themeManager`, `notificationManager`, `cacheManager` for centralized state
- **Route Guards**: Auto-redirect to login for protected pages via `app.js` interceptors  
- **Caching Strategy**: 5-minute local cache with automatic expiration checks via `cacheManager`
- **Mock Mode**: Offline development support with simulated data
- **Event System**: Listener pattern for cross-component communication
- **Theme System**: Complete dark mode support with system theme following and manual override
- **Voice Input**: Real-time speech recognition with AI-powered contact field parsing

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

### Test Users
- **Primary test user**: `wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q` (use for all tests)
- **Development users**: `dev_user_001` (auto-selected in dev environment)
- **Manual test users**: `test_user_001`, `test_user_002`, `demo_user_001`

### Backend Testing
```bash
python tests/test_api.py                 # Run full test suite
python test_intent_system.py             # Test intent matching
python test_hybrid_matching.py           # Test hybrid scoring
python test_integrated_system.py         # Integration tests
```

### Frontend Testing
- **Mock Mode**: 5 pre-configured contacts for offline testing
- **Dev Mode**: Auto-uses `dev_user_001` in WeChat Developer Tools
- **Settings Page**: Switch between WeChat login, test accounts, and mock mode

## Common Development Tasks

### Adding New Features

**Backend (Python/FastAPI)**:
1. **New API endpoint**: Edit `src/core/main.py`
2. **Business logic**: Add to `src/services/`
3. **Database changes**: Update `src/database/database_sqlite_v2.py`
4. **Test**: Add tests to `tests/test_api.py`

**Frontend (WeChat Mini Program)**:
1. **New page**: Create folder in `pages/` with `.js/.json/.wxml/.wxss` files
2. **Register page**: Add to `app.json` pages array
3. **Protected page**: Add to `app.js` protectedPages array (line 184-189)
4. **API client**: Update `utils/api-client.js` and `utils/data-manager.js`

### Working with Intent Matching

```python
# Test intent matching quickly
from src.services.intent_matcher import intent_matcher

# Match intent with all profiles
matches = intent_matcher.match_intent_with_profiles(
    intent_id=1, 
    user_id="wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
)

# Match profile with all intents
matches = intent_matcher.match_profile_with_intents(
    profile_id=1,
    user_id="wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
)
```

### Modifying Scoring Algorithm
- **Scoring weights**: Edit `src/services/intent_matcher.py` → `_calculate_match_score()`
- **AI embeddings**: Edit `src/services/vector_service.py` → `generate_embedding()`
- **Hybrid matching**: Edit `src/services/hybrid_matcher.py`

## Troubleshooting

### Common Issues

**Backend Issues**:
- **Login fails**: Check backend is running on port 8000, verify `.env` credentials
- **AI analysis fails**: Verify `QWEN_API_KEY` in `.env`, check API quotas
- **Database errors**: Run `python scripts/create_intent_tables.py` to initialize
- **WeChat callback errors**: Verify `WEWORK_TOKEN` and `WEWORK_AES_KEY` match platform config

**Frontend Issues**:
- **TDesign components missing**: Tools → Build npm in WeChat Developer Tools
- **No data displayed**: Check API server URL in `utils/constants.js`
- **Page not found**: Verify page is registered in `app.json`
- **Auth errors**: Clear local data in Settings page and re-login

### Debug Tools

**Backend**:
- Console logs in uvicorn output
- `python scripts/db_viewer_sqlite.py` - Interactive database viewer
- FastAPI docs at `http://localhost:8000/docs`

**Frontend**:
- WeChat Developer Tools Console
- Network panel for API debugging
- Settings page → "View Storage Info"

## Latest Features (Recent Updates)

### Advanced Intent Matching System

**AI-powered contact matching engine with hybrid scoring**:
- **Dual-Trigger Mechanism**: Intent-to-profiles and profile-to-intents matching
- **Hybrid Scoring**: Vector similarity (30-40%) + keyword matching (30-40%) + conditions (25-40%)
- **AI Enhancement**: Qwen API embeddings with semantic similarity calculation
- **Real-time Notifications**: Push notifications for new matches with spam prevention
- **Feedback Learning**: User feedback integration for improving match accuracy

**Core Implementation**:
```python
# Intent matching workflow
from src.services.intent_matcher import intent_matcher

# Match intent with all profiles
matches = intent_matcher.match_intent_with_profiles(
    intent_id=1, 
    user_id="wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
)

# Match profile with all intents
matches = intent_matcher.match_profile_with_intents(
    profile_id=1,
    user_id="wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
)
```

### Deep Dark Mode System

**Complete theme management with system integration**:
- **Theme Manager**: `utils/theme-manager.js` - Singleton for theme operations
- **Auto Theme**: Follows system theme changes automatically  
- **Manual Override**: User can manually set preferred theme
- **Navigation Bar**: Automatic color updates during theme transitions
- **Color System**: Comprehensive light/dark color schemes built-in
- **Component Integration**: Easy theme application via `applyToPage(page)`

**Usage**:
```javascript
import themeManager from '../utils/theme-manager';

// In page onLoad
themeManager.applyToPage(this);

// Manual theme control
themeManager.toggleTheme();
themeManager.setTheme('dark');
const currentTheme = themeManager.getTheme();
const colors = themeManager.getThemeColors();
```

### Advanced Voice Input System

**Real-time speech recognition with AI parsing**:
- **Recording Modes**: Press-and-hold or tap-to-toggle recording
- **Real-time Display**: Live speech recognition results during recording
- **AI Field Parsing**: Intelligent extraction of contact information into form fields
- **State Management**: Robust recording state with visual feedback
- **Error Recovery**: Graceful handling of recognition failures
- **Multi-field Support**: Automatically fills name, phone, company, position, etc.

**Voice Integration Points**:
- Contact forms (create/edit)
- Real-time results overlay
- AI-powered field mapping
- Fallback to manual input

### Enhanced Management System

**New utility managers**:
- **Cache Manager**: `utils/cache-manager.js` - Advanced caching with namespaces
- **Notification Manager**: `utils/notification-manager.js` - Push notification handling
- **Theme Manager**: Complete theme system as described above
- **Enhanced Auth**: Improved authentication flow with better error handling

## Key Files Reference

### Backend Core Services (WeiXinKeFu/)
- `src/services/intent_matcher.py` - Intent matching engine with hybrid scoring
- `src/services/vector_service.py` - AI embeddings and semantic search using Qwen API
- `src/services/push_service.py` - Push notification system with spam prevention
- `src/services/hybrid_matcher.py` - Advanced matching algorithms
- `src/services/ai_service.py` - AI profile extraction and analysis
- `src/core/main.py` - All API endpoints including intent management
- `src/handlers/message_handler.py` - WeChat message processing pipeline
- `src/database/database_sqlite_v2.py` - Multi-user database with intent tables

### Frontend Core Systems (weixi_minimo/)
- `utils/theme-manager.js` - Complete theme system management
- `utils/cache-manager.js` - Advanced caching with TTL and namespaces
- `utils/notification-manager.js` - Push notification coordination
- `utils/auth-manager.js` - Enhanced authentication management
- `utils/data-manager.js` - Data fetching with cache integration
- `pages/intent-manager/intent-manager.js` - Intent creation and management UI
- `pages/matches/matches.js` - Match results display and feedback
- `components/custom-tabbar/index.js` - Navigation with intent badge system

### Configuration
- `WeiXinKeFu/.env` - Backend environment variables including Qwen API key
- `weixi_minimo/utils/constants.js` - Frontend configuration
- `weixi_minimo/app.json` - Mini program pages and components
- `weixi_minimo/utils/theme-manager.js` - Theme system configuration and color schemes
- `weixi_minimo/styles/theme-dark.wxss` - Dark mode global styles