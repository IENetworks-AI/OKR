# OKR PROJECT - Repository Structure & Team Responsibilities

🚀 **Professional repository setup for AI and Data Engineering teams to collaborate seamlessly on our OKR project.**

## 👥 Team Structure

### AI Team (3 members)
- **Models**: ML model development and training
- **Training**: Model training pipelines and experiments  
- **Inference APIs**: Model serving and API endpoints
- **Research**: Jupyter notebooks and experimentation

### Data Engineering Team (3 members)
- **Kafka Ingestion**: Real-time data streaming setup
- **Airflow DAGs**: ETL pipeline orchestration
- **ETL Processing**: Data transformation and cleaning
- **DB Storage**: Database management and optimization

### Common/Shared Responsibilities
- **Configs**: Shared configuration management
- **Logging & Monitoring**: System observability
- **Tests**: Unit and integration testing
- **Utilities**: Shared helper functions and tools

### Deployment (Admin)
- **Nginx**: Web server configuration
- **Systemd**: Service management
- **GitHub Actions**: CI/CD pipeline automation

## 📂 Repository Structure

```
okr-project/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Linting, tests, build
│       └── cd.yml                 # Deploy to Oracle server
│
├── ai/                            # AI team's workspace
│   ├── notebooks/                 # Experiment Jupyter notebooks
│   ├── models/                    # Trained models, checkpoints
│   ├── src/                       # Model training & inference code
│   │   ├── training/              # Training scripts
│   │   ├── inference/             # API and inference code
│   │   └── utils/                 # AI utilities
│   └── tests/                     # Unit & integration tests
│
├── data/                          # Data engineering workspace
│   ├── kafka/                     # Kafka producers/consumers
│   │   ├── producers/             # Data producers
│   │   └── consumers/             # Data consumers
│   ├── airflow_dags/              # ETL DAGs
│   ├── scripts/                   # Transformation & cleaning scripts
│   └── tests/                     # Unit tests for pipelines
│
├── infra/                         # Deployment scripts & configs
│   ├── nginx/                     # Nginx server config
│   ├── oracle/                    # Deployment scripts for Oracle server
│   ├── airflow/                   # Airflow config files
│   └── kafka/                     # Kafka setup configs
│
├── docs/                          # Documentation
│   ├── architecture.md            # System design & diagrams
│   ├── ai_team_guidelines.md      # AI dev workflow
│   ├── data_team_guidelines.md    # Data eng workflow
│   └── deployment.md              # Deployment instructions
│
├── config/                        # Configuration files
│   ├── development.yaml           # Dev environment config
│   ├── staging.yaml               # Staging environment config
│   └── production.yaml.example    # Production config template
│
├── shared/                        # Common utilities
│   ├── logging/                   # Logging configuration
│   ├── monitoring/                # Monitoring tools
│   ├── utils/                     # Shared utilities
│   └── tests/                     # Shared tests
│
├── requirements.txt               # Python dependencies
├── setup.py                       # Package setup
├── .gitignore                     # Git ignore rules
├── .pre-commit-config.yaml        # Pre-commit hooks
├── pytest.ini                     # Test configuration
└── README.md                      # This file
```

## 🔄 Workflow & GitHub Actions

### Branch Strategy
- `main` → Production (protected, only via PR + review)
- `dev-ai` → AI development branch
- `dev-data` → Data engineering development branch
- `feature/*` → Feature development branches

### GitHub Actions
- **`ci.yml`** → Runs linting, unit tests, integration tests
- **`cd.yml`** → Deploys to Oracle server (with Nginx) if CI passes

### Development Workflow
1. Create feature branch from respective dev branch
2. Develop and test locally
3. Create Pull Request to dev branch
4. Code review and approval
5. Merge to dev branch
6. Integration testing
7. Merge to main (triggers deployment)

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Git
- Docker (optional, for local development)

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd okr-project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Start development server (if applicable)
# For AI APIs: uvicorn ai.src.inference.main:app --reload
# For data services: python data/scripts/start_services.py
```

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/okr_db

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=okr_

# Airflow
AIRFLOW_HOME=./airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor

# API Keys (add your keys)
OPENAI_API_KEY=your_openai_key
HUGGINGFACE_API_KEY=your_hf_key

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific team tests
pytest ai/tests/          # AI team tests
pytest data/tests/        # Data team tests
pytest shared/tests/      # Shared tests

# Run with coverage
pytest --cov=. --cov-report=html
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [AI Team Guidelines](docs/ai_team_guidelines.md)
- [Data Team Guidelines](docs/data_team_guidelines.md)
- [Deployment Guide](docs/deployment.md)

## 🔧 Development Tools

### Code Quality
- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **isort**: Import sorting
- **Pre-commit**: Git hooks

### Testing
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities

### AI/ML Tools
- **Jupyter**: Interactive development
- **MLflow**: Experiment tracking
- **Weights & Biases**: Model monitoring
- **TensorBoard**: Visualization

### Data Engineering Tools
- **Apache Airflow**: Workflow orchestration
- **Apache Kafka**: Stream processing
- **PostgreSQL**: Primary database
- **Redis**: Caching and queues

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Team

- **AI Team**: 3 members
- **Data Engineering Team**: 3 members
- **DevOps/Admin**: Repository maintenance

## 🔗 Links

- [Project Board](https://github.com/your-org/okr-project/projects)
- [Issues](https://github.com/your-org/okr-project/issues)
- [Wiki](https://github.com/your-org/okr-project/wiki)
- [Releases](https://github.com/your-org/okr-project/releases)