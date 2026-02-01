# Pain Narratives: AI-Powered Fibromyalgia Assessment Tool

A comprehensive research platform for evaluating fibromyalgia patient pain narratives using artificial intelligence models. This system provides automated scoring for pain severity and disability levels, supporting both individual assessments and large-scale research studies.

**Built with modern Python practices**: SQLModel, UV package manager, type safety, multilingual support, and modular architecture.

## 🎯 Project Overview

The Pain Narratives project is designed to assist healthcare researchers and clinicians in analyzing written descriptions of pain experiences from fibromyalgia patients. Using OpenAI's language models, the system provides:

- **Automated Dimensions evaluation**: AI-powered evaluation of pain severity and disability levels
- **Research Analytics**: Statistical analysis and agreement metrics for research validation
- **Batch Processing**: Efficient processing of large datasets
- **Interactive Web Interface**: User-friendly Streamlit application for easy access
- **Evaluation Group Management**: Systematic tracking and execution of AI model experiments (displayed as "Evaluation groups" in UI)
- **User Management**: Complete user registration and administration system
- **Type-Safe Architecture**: Built with SQLModel for robust database operations
- **Multilingual Support**: Full localization system with English and Spanish translations

## 🏗️ Architecture

```
pain_narratives/
├── src/
│   └── pain_narratives/          # Core Python package
│       ├── core/                 # Database and core functionality
│       │   ├── database.py      # SQLModel-based database operations
│       │   ├── openai_client.py # OpenAI API integration
│       │   └── analytics.py     # Analytics and metrics
│       ├── config/               # Configuration management
│       │   └── settings.py      # YAML-based configuration
│       ├── db/                   # Database models and migrations
│       │   ├── models_sqlmodel.py # SQLModel database models
│       │   └── alembic/         # Database migration scripts
│       ├── ui/                   # Streamlit application
│       │   ├── app.py           # Main Streamlit interface
│       │   ├── components/      # UI components
│       │   └── utils/           # Utility functions
│       ├── experiments/          # Experiment management
│       ├── analysis/            # Analytics and metrics
│       ├── utils/               # Utility functions
│       └── locales/             # Internationalization files (en.yml, es.yml)
├── scripts/                     # Management and utility scripts
│   ├── setup/                   # Database setup scripts
│   ├── register_user.py         # Interactive user registration
│   ├── manage_users.py          # User management commands
│   └── run_app.py              # Application entry point
├── tests/                       # Test suites
├── sql/                         # Database schema scripts
└── docs/                        # Documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- OpenAI API key
- UV package manager (recommended)

### Quick Start with Docker (Recommended)

The easiest way to get started is using Docker Compose, which sets up both the PostgreSQL database and application:

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd pain-narratives-app
   ```

2. **Set up configuration**:

   ```bash
   # Copy the example configuration
   cp config.yaml.example config.yaml

   # Edit config.yaml with your OpenAI API key
   # Get your key from: https://platform.openai.com/api-keys
   ```

3. **Start the PostgreSQL database**:

   ```bash
   # Start only the database (recommended for development)
   docker compose up -d postgres
   ```

4. **Initialize the database and create admin user**:

   ```bash
   # Install dependencies
   uv sync

   # Run database migrations
   cd src/pain_narratives/db && uv run alembic upgrade head && cd ../../..

   # Create your first admin user
   uv run python scripts/register_user.py
   ```

5. **Start the application**:

   ```bash
   uv run streamlit run scripts/run_app.py
   ```

6. **Access the application** at `http://localhost:8501`

### Manual Installation (Without Docker)

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd pain_narratives
   ```

2. **Install dependencies using UV**:

   ```bash
   uv sync
   ```

3. **Install the package in editable mode**:

   ```bash
   uv pip install -e .
   ```

4. **Configure the application**:
   Create a `.yaml` file in the project root (or `~/.yaml` in your home directory):

   ```yaml
   openai:
     api_key_pain_narratives: your_openai_api_key_here
     org_id: your_openai_org_id_here

   pg-prod:
     password: your_database_password
     host: localhost
     database: pain_narratives
     user: pain_narratives
     port: 5432

   models:
     default_model: gpt-5-mini
     default_temperature: 1.0
     default_top_p: 1.0
     default_max_tokens: 8000

   app:
     data_root_path: "./data"
     environment: development
     streamlit_server_port: 8501
     streamlit_server_address: localhost
   ```

5. **Set up PostgreSQL database**:

   ```bash
   # Create database and user (requires PostgreSQL admin access)
   psql -U postgres -c "CREATE USER pain_narratives WITH PASSWORD 'your_password';"
   psql -U postgres -c "CREATE DATABASE pain_narratives OWNER pain_narratives;"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE pain_narratives TO pain_narratives;"

   # Create schema
   psql -U pain_narratives -d pain_narratives -c "CREATE SCHEMA IF NOT EXISTS pain_narratives_app;"

   # Run migrations
   cd src/pain_narratives/db && uv run alembic upgrade head && cd ../../..

   # Create your first admin user
   uv run python scripts/register_user.py
   ```

### Running the Application

**Streamlit Web Interface**:

```bash
uv run streamlit run scripts/run_app.py
```

**Using Make** (recommended):

```bash
make app
```

### Full Docker Deployment

To run both the database and application in Docker:

```bash
# Start everything (database + app)
docker compose --profile full up -d

# View logs
docker compose logs -f app
```

### EC2 Deployment with HTTPS

Use the deployment script to set up Nginx with HTTPS and a systemd service:

```bash
sudo ./scripts/deploy_ec2.sh your-domain.example.com you@example.com
```

The service will start the Streamlit app on boot and automatically restart on failure.

## 🌍 Localization and Internationalization

The application supports multiple languages through a comprehensive localization system.

### Supported Languages

- **English (en)**: Primary language with complete coverage
- **Spanish (es)**: Full translation for Spanish-speaking users

### Language Switching

Users can switch between languages using the language selector in the sidebar. The interface includes:

- **Complete UI Translation**: All buttons, labels, headers, and messages
- **User-Friendly Terminology**: "Evaluation groups" in UI (internally managed as "experiment_group")
- **Dynamic Content**: Error messages, success notifications, and user feedback
- **Hierarchical Organization**: Organized translation keys for maintainability

### For Developers

**Adding New Translatable Text**:

1. Add keys to both `src/pain_narratives/locales/en.yml` and `es.yml`
2. Use the localization system in components:

```python
from pain_narratives.ui.utils.localization import get_translator

def my_component():
    t = get_translator(st.session_state.get("language", "en"))
    st.header(t("my_section.header"))
    st.button(t("common.save"))
```

**Localization Files Structure**:

```yaml
# Example localization structure
app:
  title: "AINarratives Evaluation Platform"
sidebar:
  evaluation_groups: "Evaluation groups"
  language_select: "Language / Idioma"
common:
  save: "Save"
  cancel: "Cancel"
auth:
  welcome_user: "Welcome, {username}!"
```

## 👥 User Management

The application includes a comprehensive user management system for controlling access and administration.

### User Registration

**Interactive Registration**:

```bash
# Register users with interactive prompts
uv run python scripts/register_user.py
```

**Batch Registration**:

```bash
# Create regular users
uv run python scripts/register_user_batch.py doctor_smith password123

# Create admin users
uv run python scripts/register_user_batch.py admin_user securepass --admin
```

### User Administration

**List all users**:

```bash
uv run python scripts/manage_users.py list
```

**Show user details**:

```bash
uv run python scripts/manage_users.py show username
```

**Grant admin privileges**:

```bash
uv run python scripts/manage_users.py make-admin username
```

**Reset passwords**:

```bash
uv run python scripts/manage_users.py reset-password username newpassword
```

**Delete users**:

```bash
uv run python scripts/manage_users.py delete username
```

### User Types

- **Admin Users**: Can access all Evaluation groups, manage other users, and perform administrative tasks
- **Regular Users**: Can login, create their own Evaluation groups, and run evaluations

See [docs/archive/USER_MANAGEMENT.md](docs/archive/USER_MANAGEMENT.md) for detailed user management documentation.

## �📊 Features

### 1. Streamlit Web Application

The main interface provides five key tabs:

#### **Single Narrative Evaluation**

- Input individual pain narratives for immediate AI assessment
- Real-time scoring for pain severity and disability levels
- Detailed results with confidence metrics

#### **Batch Processing**

- Upload CSV files for bulk narrative evaluation
- Progress tracking and downloadable results
- Support for large datasets with efficient processing

#### **Prompt Customization**

- Modify AI prompts for different assessment criteria
- Test and validate custom prompting strategies
- Export optimized prompts for research use

#### **Analytics & Insights**

- Statistical analysis of evaluation results
- Agreement metrics and reliability measures
- Visualization of assessment patterns

#### **Help & Documentation**

- Interactive tutorials and usage guides
- API documentation and examples
- Best practices for research applications

### 2. Database Management

**SQLModel Integration**:

- Modern type-safe database operations using SQLModel
- Automatic data validation and serialization
- Comprehensive relationship management
- Migration support through Alembic

**Key Models**:

- `User`: User accounts with authentication and authorization
- `ExperimentGroup`: Research experiment organization
- `Narrative`: Patient pain descriptions and metadata
- `EvaluationResult`: Processed assessment results
- `UserPrompt`: Custom prompt configurations

**Database Features**:

- PostgreSQL with schema-based organization
- Automatic connection pooling and session management
- Transaction safety and rollback support
- Efficient querying with SQLModel's select syntax

### 3. Experiment Management

**Systematic Research Support**:

- Git-integrated experiment tracking
- Reproducible research workflows
- Automated result documentation

**Features**:

- Version control integration
- Parameter optimization
- Result comparison and analysis

### 4. AI Model Integration

**OpenAI API Integration**:

- Support for multiple model variants (GPT-4o, gpt-5-mini, GPT-4-turbo)
- Customizable prompting strategies
- Response validation and error handling

**Assessment Capabilities**:

- Pain severity scoring (0-10 scale)
- Disability level evaluation
- Confidence and reliability metrics

## 🔧 Configuration

The application uses a centralized YAML configuration system located at `~/.yaml` in your home directory:

```yaml
openai:
  api_key: your_openai_api_key_here
  api_key_pain_narratives: your_pain_narratives_api_key_here
  org_id: your_openai_org_id_here

pg:
  password: your_database_password
  host: your_database_host
  database: your_database_name
  user: your_database_user
  port: 5432

models:
  default_model: gpt-5-mini
  default_temperature: 1.0
  default_top_p: 1.0
  default_max_tokens: 8000

app:
  data_root_path: "./data"
  environment: development
  streamlit_server_port: 8501
  streamlit_server_address: localhost

# Optional: AWS Bedrock configuration for alternative AI models
bedrock:
  aws_credentials: your_aws_profile_name
  aws_access_key: your_aws_access_key
  aws_secret_key: your_aws_secret_key
  aws_region: your_aws_region
```

### Configuration Benefits

- **Centralized**: All configuration in one place (`~/.yaml`)
- **Shared**: Same configuration file can be used across multiple projects
- **Secure**: Sensitive credentials stored outside the project directory
- **Flexible**: Easy to switch between environments and configurations

## 📚 API Reference

### Core Classes

#### `DatabaseManager`

Modern SQLModel-based database operations with singleton pattern:

```python
from pain_narratives.core.database import DatabaseManager

# Get the singleton instance
db = DatabaseManager()

# User management
user = db.create_user(username="researcher", password="secure123", is_admin=False)
user_info = db.authenticate_user("researcher", "secure123")

# Evaluation Groups (using experiment_group methods internally)
groups = db.get_experiment_groups_for_user(user_id=1, is_admin=False)
group = db.create_experiment_group(
    owner_id=1,
    description="Pain severity analysis",
    system_role="You are an expert physician...",
    base_prompt="Evaluate the following narrative..."
)

# SQLModel session management
with db.get_session() as session:
    from sqlmodel import select
    from pain_narratives.db.models_sqlmodel import User
    users = session.exec(select(User)).all()
```

#### `ExperimentRunner`

```python
from pain_narratives.experiments.runner import ExperimentRunner

runner = ExperimentRunner()
results = runner.run_experiment(
    experiment_name="pain_severity_v1",
    narratives=narrative_list,
    prompts=custom_prompts
)
```

#### `OpenAIClient`

Type-safe OpenAI integration with error handling:

```python
from pain_narratives.core.openai_client import OpenAIClient

client = OpenAIClient()
response = client.get_completion(
    prompt="Evaluate this pain narrative...",
    model="gpt-5-mini",
    temperature=0.0
)
```

### Database Schema (SQLModel)

### Database Schema (SQLModel)

**Users Table** (SQLModel):

```python
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False, max_length=255)
    is_admin: bool = Field(default=False, nullable=False)

    experiments_groups: List["ExperimentGroup"] = Relationship(back_populates="owner")
    prompts: List["UserPrompt"] = Relationship(back_populates="user")
```

**Narratives Table** (SQLModel):

```python
class Narrative(SQLModel, table=True):
    narrative_id: int = Field(primary_key=True)
    narrative: Optional[str] = None
    owner_id: int = Field(foreign_key="users.id")
    narrative_hash: Optional[str] = Field(default=None, max_length=64)
    word_count: Optional[int] = Field(default=None)
    char_count: Optional[int] = Field(default=None)

    experiments: List["ExperimentList"] = Relationship(back_populates="narrative")
    owner: Optional["User"] = Relationship(back_populates="narratives")
    evaluation_results: List["EvaluationResult"] = Relationship(back_populates="narrative")
```

**Evaluation Groups Table** (SQLModel - `ExperimentGroup` model):

```python
class ExperimentGroup(SQLModel, table=True):
    experiments_group_id: Optional[int] = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=datetime.now(timezone.utc), nullable=False)
    description: Optional[str] = None
    system_role: Optional[str] = None
    base_prompt: Optional[str] = None
    concluded: bool = Field(default=False, nullable=False)
    processed: bool = Field(default=False, nullable=False)
    owner_id: int = Field(foreign_key=f"{SCHEMA_NAME}.users.id")

    owner: Optional["User"] = Relationship(back_populates="experiments_groups")
    experiments: List["ExperimentList"] = Relationship(back_populates="group")
```

## 🧪 Usage Examples

### Basic Narrative Evaluation

```python
from pain_narratives.core.database import DatabaseManager
from pain_narratives.experiments.runner import ExperimentRunner

# Initialize components (singleton pattern)
db = DatabaseManager()
runner = ExperimentRunner()

# Evaluate a single narrative
narrative = "The pain in my joints is constant and severe..."
result = runner.evaluate_narrative(narrative)

print(f"Pain Severity: {result['pain_severity']}")
print(f"Disability Level: {result['disability_level']}")
print(f"Confidence: {result['confidence']}")
```

### User Management

```python
from pain_narratives.core.database import DatabaseManager
from sqlmodel import select
from pain_narratives.db.models_sqlmodel import User

db = DatabaseManager()

# Create a new user
user = db.create_user(
    username="researcher_01",
    password="secure_password",
    is_admin=False
)

# Authenticate user
auth_result = db.authenticate_user("researcher_01", "secure_password")
if auth_result:
    print(f"User {auth_result['username']} authenticated successfully")

# List all users (using SQLModel)
with db.get_session() as session:
    users = session.exec(select(User)).all()
    for user in users:
        print(f"User: {user.username}, Admin: {user.is_admin}")
```

### Type-Safe Database Operations

```python
from pain_narratives.core.database import DatabaseManager
from pain_narratives.db.models_sqlmodel import ExperimentGroup
from sqlmodel import select

db = DatabaseManager()

# Create Evaluation group with type safety (using experiment_group methods internally)
group = db.create_experiment_group(
    owner_id=1,
    description="Fibromyalgia Dimensions evaluation study",
    system_role="You are an expert pain specialist...",
    base_prompt="Evaluate the following pain narrative..."
)

# Query with SQLModel's type-safe select
with db.get_session() as session:
    # Get all Evaluation groups for a user (using ExperimentGroup model internally)
    user_groups = session.exec(
        select(ExperimentGroup).where(ExperimentGroup.owner_id == 1)
    ).all()

    # Get groups with specific criteria
    active_groups = session.exec(
        select(ExperimentGroup).where(
            ExperimentGroup.concluded == False,
            ExperimentGroup.owner_id == 1
        )
    ).all()
```

### Batch Processing

```python
import pandas as pd

# Load narratives from CSV
df = pd.read_csv('patient_narratives.csv')
narratives = df['narrative_text'].tolist()

# Process batch
results = runner.batch_evaluate(narratives, batch_size=25)

# Save results
results_df = pd.DataFrame(results)
results_df.to_csv('evaluation_results.csv', index=False)
```

### Custom Prompt Experiment

```python
# Define custom prompts
pain_prompt = """
Evaluate the pain severity described in this narrative on a scale of 0-10,
where 0 is no pain and 10 is the worst pain imaginable.
Consider both intensity and impact on daily activities.
"""

# Run experiment with custom prompt
experiment_results = runner.run_experiment(
    experiment_name="custom_pain_assessment",
    narratives=test_narratives,
    prompts={'pain_severity': pain_prompt}
)
```

## 📈 Analytics and Metrics

### Agreement Analysis

The system provides comprehensive analytics for research validation:

- **Inter-rater Reliability**: Cohen's Kappa and weighted Kappa
- **Consistency Metrics**: Root Mean Square Error (RMSE)
- **Distribution Analysis**: Score distribution and outlier detection

### Performance Metrics

```python
from pain_narratives.core.analytics import evaluate_agreement_metrics

# Calculate agreement between AI and human evaluators
kappa_score = evaluate_agreement_metrics(
    expert1_scores=human_evaluations,
    expert2_scores=other_expert_evaluations,
    model_scores=ai_evaluations,
)["expert1_model_kappa"]
```

## 🛠️ Development

### Modern Python Development Setup

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd pain_narratives
   ```

2. **Install development dependencies with UV**:

   ```bash
   uv sync --dev
   ```

3. **Install the package in editable mode**:

   ```bash
   uv pip install -e .
   ```

4. **Set up pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

### Package Management with UV

The project uses UV for modern Python package management:

```bash
# Sync dependencies
uv sync

# Add new dependencies
uv add sqlmodel pydantic

# Add development dependencies
uv add --dev pytest mypy

# Run commands in the UV environment
uv run python scripts/run_app.py
uv run pytest
uv run mypy src/
```

### SQLModel Development

The project uses SQLModel for type-safe database operations:

```python
# Example: Adding a new model
from sqlmodel import SQLModel, Field
from typing import Optional, List

class NewModel(SQLModel, table=True):
    __tablename__ = "new_table"
    __table_args__ = {"schema": SCHEMA_NAME}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False)
    # Add relationships as needed
```

### Running Tests

```bash
# Run all tests with UV
uv run pytest

# Run with coverage
uv run pytest --cov=src/pain_narratives

# Run specific test suite
uv run pytest tests/test_database.py

# Test imports without path hacks
uv run python tests/verify_imports.py
```

### Code Quality

The project enforces modern Python development practices:

- **Type Safety**: Full type annotations with SQLModel and mypy
- **Code Formatting**: Black for consistent code style
- **Import Management**: isort for organized imports
- **Linting**: flake8 for code quality
- **Package Management**: UV for fast, reliable dependency resolution
- **No Path Hacks**: Proper editable installation eliminates sys.path manipulation

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Run linting
uv run flake8 src/ tests/

# Type checking with SQLModel support
uv run mypy src/

# Run all quality checks
uv run pre-commit run --all-files
```

### Publication Analysis Pipeline

The project includes a complete pipeline for running analysis notebooks and consolidating results:

```bash
# Run all 14 analysis notebooks in sequence
make run-notebooks

# Run notebooks with continue-on-error (won't stop on failures)
make run-notebooks-safe

# List all analysis notebooks without executing
make list-notebooks

# Consolidate all publication CSV files into one Excel workbook
make consolidate-tables

# Full pipeline: run all notebooks + consolidate tables
make publication
```

**Output**: The consolidation script creates `notebooks/outputs/publication/publication_tables.xlsx` with 27 sheets including:

- Publication tables (T1-T14): Sample characteristics, dimension results, correlations, feedback analysis
- Data exports: PCS, BPI, TSK questionnaire results (152 rows each)
- Correlation details: LLM consistency, LLM-expert agreement, synthetic-expert comparisons
- Additional data: Excel ID mappings, SUS usability responses

### Project Structure Best Practices

- **src/ layout**: Proper Python package structure
- **SQLModel models**: Type-safe database operations
- **Singleton patterns**: Efficient resource management
- **Configuration management**: Centralized YAML-based config
- **Script organization**: Clear separation of concerns
- **UV integration**: Modern dependency management

## 🚀 Migration to SQLModel & UV

This project has been fully migrated to use modern Python tooling:

### ✅ Completed Migrations

- **SQLModel**: Replaced legacy SQLAlchemy with type-safe SQLModel
- **UV Package Manager**: Modern, fast dependency management
- **Editable Installation**: No more `sys.path` manipulation
- **Type Safety**: Full type annotations throughout
- **User Management**: Complete user registration and administration
- **Hatch Integration**: Proper development environment setup

### Key Benefits

- **Type Safety**: Catch errors at development time
- **Performance**: Faster dependency resolution with UV
- **Maintainability**: Clean, modern code structure
- **Developer Experience**: Better IDE support and tooling integration
- **Standards Compliance**: Following Python packaging best practices

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure code quality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Contribution Guidelines

- Follow the existing code style and conventions
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting PR
- Include clear commit messages and PR descriptions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for providing the language models that power the assessment system
- The fibromyalgia research community for validation and feedback
- Contributors and maintainers of the open-source libraries used in this project

## 📞 Support

For questions, issues, or contributions:

- **Issues**: Please use the GitHub issue tracker
- **Documentation**: See the `/docs` directory for detailed guides
- **Research Inquiries**: Contact the research team for collaboration opportunities

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and updates.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes using modern practices:
   - Follow SQLModel patterns for database operations
   - Use UV for dependency management
   - Ensure type safety with mypy
   - Run code quality checks
4. Run tests and ensure code quality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Contribution Guidelines

- **Type Safety**: All new code should include type annotations
- **SQLModel**: Use SQLModel for all database operations
- **UV**: Use UV for dependency management (`uv add package-name`)
- **Code Quality**: Follow PEP8 and use the provided code quality tools
- **Testing**: Write comprehensive tests for new features
- **Documentation**: Update docstrings and README for API changes
- **No Path Hacks**: Use proper imports with editable installation

### Development Workflow

```bash
# Setup development environment
uv sync --dev
uv pip install -e .

# Make changes and test
uv run pytest
uv run mypy src/
uv run pre-commit run --all-files

# Add dependencies properly
uv add new-package
uv add --dev dev-package

# Test user management
uv run python scripts/manage_users.py list
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **SQLModel**: For providing type-safe database operations
- **UV**: For modern Python package management
- **OpenAI**: For providing the language models that power the assessment system
- **Streamlit**: For the interactive web interface framework
- **PostgreSQL**: For robust database backend
- **The fibromyalgia research community**: For validation and feedback

## 📞 Support

For questions, issues, or contributions:

- **Issues**: Please use the GitHub issue tracker
- **Documentation**: See the `/docs` directory and inline docstrings
- **User Management**: See [docs/archive/USER_MANAGEMENT.md](docs/archive/USER_MANAGEMENT.md)
- **Research Inquiries**: Contact the research team for collaboration opportunities

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and updates.

### Recent Major Updates

- ✅ **SQLModel Migration**: Complete migration from legacy SQLAlchemy to type-safe SQLModel
- ✅ **UV Package Manager**: Modern dependency management with UV
- ✅ **User Management System**: Complete user registration and administration
- ✅ **Type Safety**: Full type annotations and mypy compliance
- ✅ **Editable Installation**: Eliminated sys.path manipulation
- ✅ **Modern Architecture**: Clean separation of concerns and best practices

---

**Note**: This project is designed for research purposes. Please ensure compliance with relevant healthcare data regulations and institutional review board requirements when working with patient data.
