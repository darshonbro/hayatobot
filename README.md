# Hayato On Fire — Advanced Discord Role Management Bot

A production-ready, asynchronous Discord role management bot built with **Python 3.11+**, **discord.py 2.x**, **SQLAlchemy 2.x**, and **SQLite / PostgreSQL**.

---

## 🌟 Key Features

- **Dynamic Role Assignment (`/role give`)**:
  - Assigns roles dynamically by Discord snowflake Role ID at runtime without hardcoding.
  - Strict permission validation (**Manage Roles** / **Administrator** / Server Owner).
  - Role hierarchy validation: prevents users or the bot from granting roles higher than or equal to their top role.
  - Rejects `@everyone` and integration-managed (bot/booster) roles.
  - Duplicate detection: members who already hold the role are not re-notified or duplicated.
- **Dynamic DM Template Engine (`/dm-config`)**:
  - Server-specific, customizable DM templates.
  - Dynamic placeholder substitution: `{user}`, `{user_name}`, `{user_id}`, `{server}`, `{role}`, `{role_id}`, `{role_description}`.
  - Unknown variables are preserved safely without throwing exceptions.
  - Mass-mention sanitization (`@everyone` and `@here` neutralized with zero-width spaces).
  - Configurable role-specific descriptions injected seamlessly into `{role_description}`.
  - Interactive live preview command (`/dm-config preview`) without sending messages.
- **Resilient Direct Message Delivery**:
  - Sends direct messages safely with `allowed_mentions` restricted.
  - If a user has DMs closed or blocks the bot (`discord.Forbidden`), the role assignment is preserved and the DM delivery failure is logged and reported.
- **Comprehensive Audit Trail (`/audit`)**:
  - Tracks timestamp, actor, target user, role ID, role name, action type, and DM status (`SENT`, `FAILED`, `SKIPPED_DUPLICATE`).
  - Query recent guild actions or target member history.
- **Multi-Server Database Isolation**:
  - Independent configurations, role descriptions, and audit logs per Discord server (`guild_id`).
  - Asynchronous SQLAlchemy 2.x with native support for SQLite (`aiosqlite`) and PostgreSQL (`asyncpg`).
- **Interactive UI Components**:
  - Ephemeral administrative responses to prevent chat spam.
  - Interactive button view for confirming configuration resets (`/config reset`).
- **Discord Bot Verification Web Portal**:
  - Built-in asynchronous web server (`aiohttp.web`) for hosting legal documents.
  - Dedicated, compliant **Terms of Service** (`/terms`) and **Privacy Policy** (`/privacy`).
  - High-performance landing page (`/`) showcasing bot features, slash commands, and invite button.
  - Automated health check endpoint (`/health`) for UptimeRobot and hosting container health checks.

---

## 📂 Project Architecture

```
Hayato_Bot/
├── bot/
│   ├── __init__.py           # Package definition & metadata
│   ├── main.py               # HayatoBot lifecycle, app command sync, global error handler
│   ├── config.py             # Configuration loader, URL normalizer, structured logging
│   ├── database.py           # SQLAlchemy 2.x AsyncEngine and session manager
│   ├── models.py             # ORM models (GuildConfig, RoleDescription, AuditLog)
│   ├── checks.py             # Permissions, role eligibility, and hierarchy validators
│   ├── services/
│   │   ├── __init__.py
│   │   ├── role_service.py   # Role assignment, removal, and DM orchestrator
│   │   ├── template_service.py # Dynamic template parsing, sanitization, and DB storage
│   │   └── audit_service.py  # Audit log persistence and queries
│   └── cogs/
│       ├── __init__.py
│       ├── role.py           # /role give, /role remove, /role info
│       ├── dm_config.py      # /dm-config set, preview, description, variables
│       ├── configuration.py  # /config view, /config reset
│       └── audit.py          # /audit recent, /audit user
├── web/
│   ├── __init__.py
│   ├── server.py             # Async aiohttp web server (Terms, Privacy, Landing, Health)
│   ├── static/
│   │   ├── css/style.css     # Dark mode glassmorphism UI styling
│   │   └── js/main.js        # Interactive frontend behaviors
│   └── templates/
│       ├── index.html        # Public bot landing page & command reference
│       ├── terms.html        # Discord Verification Compliant Terms of Service
│       └── privacy.html      # Discord Verification Compliant Privacy Policy
├── tests/
│   ├── conftest.py           # In-memory async SQLite engine & Discord object mocks
│   ├── test_template_service.py # Template substitution, isolation, sanitization
│   ├── test_role_service.py  # Assignment, duplicate checks, DM failure handling
│   ├── test_checks.py        # Hierarchy, permission, and role eligibility checks
│   ├── test_audit_service.py # Audit logging and multi-server isolation
│   ├── test_bot_setup.py     # Cogs loading and URL normalization
│   └── test_web_server.py    # Web portal endpoints (Terms, Privacy, Health)
├── .env.example              # Environment variables template
├── .gitignore                # Secrets, caches, and database ignore rules
├── requirements.txt          # Python production and testing dependencies
├── pytest.ini                # Pytest configuration
└── README.md                 # Complete documentation and setup manual
```

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.11** or higher.
- A Discord Bot Token from the [Discord Developer Portal](https://discord.com/developers/applications).

---

### 2. Windows PowerShell Setup

```powershell
# 1. Navigate to the project directory
cd d:\projects\Hayato_Bot

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1
# Note: If script execution is restricted, run:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 4. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Create your .env configuration
Copy-Item .env.example .env
notepad .env
```

---

### 3. Linux / macOS Setup

```bash
# 1. Navigate to the project directory
cd Hayato_Bot

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Copy configuration
cp .env.example .env
nano .env
```

---

## ⚙️ Environment Configuration (`.env`)

Edit your `.env` file with your credentials:

```dotenv
# Discord Bot Authentication Token (Required)
DISCORD_TOKEN=OTk5...your_actual_token_here...

# Database Connection URL
# SQLite (Default):
DATABASE_URL=sqlite+aiosqlite:///bot.db

# PostgreSQL (Production option):
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/hayato_db

# Development Guild ID (Optional):
# Set your server's numerical ID here for INSTANT slash command synchronization during testing.
# Leave blank in production for global synchronization across all servers.
DEV_GUILD_ID=123456789012345678

# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

---

## 🤖 Discord Developer Portal Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a **New Application** (e.g. `Hayato On Fire`).
2. Navigate to the **Bot** tab:
   - Click **Reset Token** to copy your bot token and paste it into `.env` under `DISCORD_TOKEN`.
   - Scroll down to **Privileged Gateway Intents** and enable:
     - ✅ **Server Members Intent** (*Crucial for resolving guild members and modifying roles*).
3. Navigate to **OAuth2 > URL Generator**:
   - Under **Scopes**, select:
     - `bot`
     - `applications.commands`
   - Under **Bot Permissions**, select:
     - `Manage Roles`
     - `View Channels`
     - `Send Messages`
     - `Embed Links`
     - `Read Message History`
4. Copy the generated authorization URL, paste it into your browser, and invite the bot to your Discord server.
5. **Server Role Positioning (Crucial)**:
   - In Discord, go to **Server Settings > Roles**.
   - Drag the bot's highest role **ABOVE** the roles you want it to assign.
   - Discord's hierarchy prevents any user or bot from managing roles positioned equal to or higher than their own top role.

---

## 📖 Slash Commands Reference

### 1. Role Commands (`/role`)

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/role give` | `member:@User` `role_id:123...` | Dynamically assigns the role to the member, delivers a personalized DM, and records an audit log. |
| `/role remove`| `member:@User` `role_id:123...` | Removes the specified role from the member and records an audit log. |
| `/role info` | `role_id:123...` | Displays role name, ID, position, member count, key permissions, and configured DM description. |

### 2. DM Configuration (`/dm-config`)

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/dm-config set` | `template:"..."` | Configures the server's reusable DM message template. |
| `/dm-config preview` | `role_id:123...` `[custom_template:"..."]` | Renders a simulated preview of the DM using the specified role without dispatching a real message. |
| `/dm-config description` | `role_id:123...` `[description:"..."]` | Saves or updates a role-specific description for the `{role_description}` placeholder. Pass blank or `clear` to remove. |
| `/dm-config variables` | *(None)* | Displays all supported template placeholders and example usage. |

### 3. General Configuration (`/config`)

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/config view` | *(None)* | Displays the active DM template and a summary of configured role descriptions for this server. |
| `/config reset` | *(None)* | Displays an interactive confirmation button prompt to restore the default factory DM template. |

### 4. Audit Commands (`/audit`)

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/audit recent` | `[limit:10]` | Shows recent role assignments, removals, timestamps, actors, and DM delivery statuses. |
| `/audit user` | `member:@User` `[limit:10]` | Shows role assignment and removal history for a specific member. |

---

## 📝 Dynamic DM Template Engine

### Supported Variables
| Variable | Description | Example Output |
| :--- | :--- | :--- |
| `{user}` | Recipient's Discord mention | `<@222222222>` |
| `{user_name}` | Recipient's display name or nickname | `SpeedyGamer` |
| `{user_id}` | Recipient's Discord snowflake ID | `222222222` |
| `{server}` | Current server name | `Hayato Arena` |
| `{role}` | Dynamically assigned role's name | `Elite Champion` |
| `{role_id}` | Numeric ID of the assigned role | `987654321012345678` |
| `{role_description}` | Role-specific description from database | `Access to VIP lounge and private channels.` |

### Default Factory Template
```
Congratulations, {user}!

You have received the {role} role.

{role_description}

Enjoy your new permissions!
```

### Example Personalized Direct Message
When `/role give member:@SpeedyGamer role_id:987654321012345678` is run with a description configured for the `Elite Champion` role:

> Congratulations, <@222222222>!
>
> You have received the **Elite Champion** role.
>
> Access to VIP lounge and private channels.
>
> Enjoy your new permissions!

---

## 🔒 Security & Permission Model

1. **Invoker Authorization**:
   - Only server owners or members with the **Manage Roles** or **Administrator** permission can execute role-assignment or configuration commands.
2. **Role Hierarchy Enforcement**:
   - The bot checks `invoker.top_role.position > target_role.position` (server owner bypasses).
   - The bot checks `bot.top_role.position > target_role.position`.
3. **Protected Roles**:
   - Prevents assignment or removal of `@everyone`.
   - Prevents assignment of managed roles (`role.managed == True`, such as bot integration roles or server booster roles).
4. **Mass-Mention Prevention**:
   - `@everyone` and `@here` strings within user display names, role names, or custom descriptions are neutralized (`@\u200beveryone`, `@\u200bhere`).
   - Direct messages are sent with `allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)`.
5. **Multi-Server Data Isolation**:
   - All database queries and updates are constrained by `guild_id`. One server can never access, overwrite, or view another server's templates, descriptions, or audit records.

---

## 🧪 Automated Testing

The project includes an automated test suite with full mocking of Discord API operations and in-memory async database fixtures.

To execute the entire test suite:

```bash
# Run tests with verbose output
python -m pytest -v
```

### Test Coverage Highlights:
- ✅ Dynamic `{role}`, `{role_id}`, `{user}`, `{server}` substitution
- ✅ Role-specific description substitution and empty fallback
- ✅ Unknown variable safe preservation
- ✅ Mass-mention neutralization (`@everyone` / `@here`)
- ✅ Template length validation and truncation safety
- ✅ Multi-server template and description isolation
- ✅ Permission validation (admin, manage_roles, server owner, unauthorized users)
- ✅ Bot and user role hierarchy validation
- ✅ Role eligibility checks (`@everyone`, managed roles)
- ✅ Duplicate role assignment detection and duplicate DM suppression
- ✅ DM delivery failure handling when member DMs are closed (`discord.Forbidden`)
- ✅ Audit log persistence, sorting, and user-filtering

---

## 🏁 Running the Bot

```bash
# Start Hayato On Fire
python -m bot.main
```

When connected, the bot logs its initialization, verifies database schemas, synchronizes slash commands, and updates its presence:
```
[2026-10-27 02:15:00] [INFO] [hayato_bot]: Starting database initialization...
[2026-10-27 02:15:00] [INFO] [hayato_bot]: Database schema verified and initialized.
[2026-10-27 02:15:00] [INFO] [hayato_bot]: Loaded extension: bot.cogs.role
[2026-10-27 02:15:00] [INFO] [hayato_bot]: Loaded extension: bot.cogs.dm_config
[2026-10-27 02:15:00] [INFO] [hayato_bot]: Loaded extension: bot.cogs.configuration
[2026-10-27 02:15:00] [INFO] [hayato_bot]: Loaded extension: bot.cogs.audit
[2026-10-27 02:15:01] [INFO] [hayato_bot]: ============================================================
[2026-10-27 02:15:01] [INFO] [hayato_bot]: 🤖 Hayato On Fire is online and ready!
[2026-10-27 02:15:01] [INFO] [hayato_bot]: ============================================================
```
