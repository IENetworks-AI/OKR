# OKR Project - ML Pipeline with Oracle Cloud Deployment

A comprehensive OKR (Objectives and Key Results) management system with machine learning capabilities, real-time data processing, and automated deployment to Oracle Cloud Infrastructure.

## 🚀 Features

- **Flask API**: RESTful API for OKR management
- **Real-time Dashboard**: Interactive web dashboard with charts and analytics
- **Kafka Streaming**: Real-time data ingestion and processing
- **Airflow Pipelines**: Automated ETL, model training, and monitoring
- **Oracle Cloud Deployment**: Automated CI/CD pipeline with GitHub Actions
- **Docker Containerization**: All services run in Docker containers
- **Branch Protection**: Strict controls with owner-only main branch access
- **Comprehensive ETL Pipeline**: Clear procedures from development to deployment
- **Sample Data Generation**: Built-in data generation for testing
- **Comprehensive Testing**: Local testing suite before deployment

## 📁 Project Structure

```
OKR/
├── api/                          # Flask API server
│   ├── app.py                   # Main API application
│   └── dashboard.html           # Interactive dashboard
├── data/                        # Data storage
│   ├── raw/                     # Raw data files
│   ├── processed/               # Intermediate data
│   ├── final/                   # Final outputs & models
│   └── README.md                # Data documentation
├── airflow_dags/                # Airflow data pipelines
│   └── dags/
│       ├── etl_pipeline.py      # ETL pipeline
│       ├── model_training_pipeline.py  # ML training
│       └── monitoring_pipeline.py      # Monitoring
├── kafka_pipeline/              # Kafka streaming
│   ├── producers/               # Data producers
│   ├── consumers/               # Data consumers
│   └── schemas/                 # Data schemas
├── configs/                     # Configuration files
│   ├── db_config.yaml          # Database configuration
│   ├── kafka_config.yaml       # Kafka configuration
│   └── model_config.yaml       # Model configuration
├── scripts/                     # Setup and utility scripts
│   ├── setup_local.py          # Local testing script
│   ├── generate_sample_data.py # Sample data generator
│   └── ...                     # Other setup scripts
├── deploy/                      # Deployment configurations
├── .github/workflows/           # GitHub Actions CI/CD
│   └── deploy.yml              # Oracle deployment workflow
└── requirements.txt             # Python dependencies
```

## 🛠️ Quick Start

### Run Everything in Docker (recommended)

1. Build images
   ```bash
   docker compose build
   ```

2. Start the full stack (always-restart policies enabled)
   ```bash
   docker compose up -d
   ```

3. Access services
   - API: `http://localhost:5001/` and dashboard at `http://localhost:5001/dashboard`
   - Nginx proxy to API: `http://localhost/`
   - Kafka UI: `http://localhost:8085/`
   - Airflow: `http://localhost:8080/` (admin/admin)
   - Oracle XE: `SYSTEM/oracle@localhost:1521/XEPDB1`

4. Validate health
   ```bash
   docker compose ps
   docker compose logs -f --tail=100
   curl http://localhost:5001/api/test-kafka
   curl http://localhost:5001/api/test-airflow
   ```

5. Stop or remove
   ```bash
   docker compose stop      # stop containers
   docker compose down      # remove containers
   ```

6. Optional: run producer/consumer again
   ```bash
   docker restart okr_producer okr_consumer
   ```

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd OKR
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run local tests**
   ```bash
   python scripts/setup_local.py
   ```

4. **Start the Flask API**
   ```bash
   cd api
   python app.py
   ```

5. **Access the dashboard**
   - Open `http://localhost:5000/dashboard` in your browser
   - Use the controls to generate sample data and test services

### Oracle Cloud Deployment

1. **Configure GitHub Secrets**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add `ORACLE_SSH_KEY` with your private SSH key

2. **Push to main branch**
   ```bash
   git add .
   git commit -m "Ready for Oracle deployment"
   git push origin main
   ```

3. **Monitor deployment**
   - Check GitHub Actions tab for deployment progress
   - The workflow will automatically deploy to Oracle Cloud

## 🔧 Configuration

### Oracle Instance Details
- **IP Address**: `139.185.33.139` (hardcoded in workflow)
- **Username**: `ubuntu`
- **Project Directory**: `/home/ubuntu/okr-project`
- **Service Name**: `mlapi.service`
- **Port**: `5000`

### Required Services
- **Flask API**: Port 5000
- **Kafka**: Port 9092
- **Airflow**: Port 8080
- **Zookeeper**: Port 2181

## 📊 Dashboard Features

The interactive dashboard provides:

- **System Status**: Real-time monitoring of all services
- **OKR Overview**: Charts showing OKR distribution and progress
- **Department Progress**: Progress tracking by department
- **Real-time Controls**: Buttons to test services and generate data
- **Activity Feed**: Live updates of system activities
- **Data Table**: Detailed view of all OKR records

## 🔄 Data Pipeline

1. **Data Ingestion**: Kafka streams real-time OKR data
2. **ETL Processing**: Airflow transforms raw data into features
3. **Model Training**: Automated ML model training pipeline
4. **Monitoring**: Continuous model performance monitoring
5. **Storage**: Organized data storage in raw/processed/final folders

## 🚀 Deployment Process

### Branch Protection & Access Control
- **Main Branch**: Only repository owners can merge to main
- **Test Branch**: All contributors can merge, triggers test deployment
- **Feature Branches**: Development and testing only
- **Required Reviews**: 2 approvals including repository owner
- **Status Checks**: All quality, security, and deployment checks must pass

### Oracle Server Deployment Workflow
The GitHub Actions workflow:

1. **Permission Validation** - Checks if user has owner permissions
2. **Oracle Secrets Check** - Validates deployment configuration
3. **SSH Connection Setup** - Establishes secure connection to Oracle
4. **Code Deployment** - Syncs project files using rsync
5. **Docker Services Setup** - Runs comprehensive setup script
6. **Service Validation** - Verifies all services are working
7. **Sample Data Generation** - Creates test data for immediate use

### Deployment Environments
- **Production**: Main branch → Oracle server (owner only)
- **Staging**: Test branch → Oracle server (all contributors)
- **Development**: Feature branches → Local Docker only

## 🧪 Testing

### Local Testing
```bash
python scripts/setup_local.py
```

This script tests:
- Sample data generation
- Flask API functionality
- Data pipeline components
- Kafka components
- Configuration files
- Deployment scripts
- Python requirements

### Service Testing
- **API Test**: `curl http://localhost:5000/`
- **Kafka Test**: Use dashboard "Test Kafka" button
- **Airflow Test**: Use dashboard "Test Airflow" button

## 📝 API Endpoints

- `GET /` - API status and health check
- `GET /dashboard` - Interactive OKR dashboard
- `GET /api/okrs` - Get all OKR data
- `POST /api/generate-sample-data` - Generate sample data
- `GET /api/test-kafka` - Test Kafka connection
- `GET /api/test-airflow` - Test Airflow connection

## 🔒 Security

- **Branch Protection**: Only repository owners can merge to main
- **SSH Keys**: Secure Oracle access using SSH keys
- **Secrets Management**: GitHub secrets for sensitive data
- **Firewall**: Oracle instance configured with minimal open ports
- **Service Isolation**: Each service runs in its own Docker container
- **Code Reviews**: Required reviews for all changes
- **Security Scans**: Automated security scanning in CI/CD

## 🐛 Troubleshooting

### Common Issues

1. **"Oracle deployment secrets not found"**
   - Configure `ORACLE_SSH_KEY` in GitHub secrets
   - Deployment will be skipped gracefully if missing

2. **SSH connection failed**
   - Verify SSH key is correct
   - Check Oracle instance firewall settings
   - Ensure instance is accessible

3. **Service startup failed**
   - Check logs: `sudo journalctl -u mlapi.service -f`
   - Verify Python environment
   - Check dependencies

### Logs and Monitoring

```bash
# Flask API logs
sudo journalctl -u mlapi.service -f

# Kafka logs
tail -f ~/okr-project/kafka/kafka.log

# Airflow logs
tail -f ~/okr-project/airflow_webserver.log
tail -f ~/okr-project/airflow_scheduler.log
```

## 📈 Monitoring

- **Service Health**: Real-time status monitoring
- **Performance Metrics**: OKR progress tracking
- **Error Logging**: Comprehensive error tracking
- **Activity Feed**: Live system activity updates

## 🔄 Updates and Maintenance

- **Automatic Updates**: Push to main branch triggers deployment
- **Rollback**: Previous versions available in Git history
- **Health Checks**: Built-in service health monitoring
- **Log Rotation**: Automatic log management

## 🤝 Contributing

### Development Workflow
1. **Fork the repository**
2. **Create a feature branch** from `develop`
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and test locally
   ```bash
   docker-compose up -d
   python scripts/setup_local.py
   ```
4. **Create pull request** to `develop` branch
   - Include description of changes
   - Link related issues
   - Request reviews from repository owners
5. **Code review process**
   - Address review comments
   - Ensure all checks pass
   - Get approval from repository owners
6. **Merge to develop** after approval

### Branch Strategy
- **Feature branches**: `feature/*` - Individual features
- **Develop branch**: Integration of features
- **Test branch**: Staging and testing
- **Main branch**: Production (owner only)

### Required for All Changes
- [ ] Code review completed
- [ ] All tests passing
- [ ] Security scan passed
- [ ] Documentation updated
- [ ] No merge conflicts

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📚 Documentation

- **[ETL Pipeline Procedures](ETL_PIPELINE_PROCEDURES.md)** - Complete ETL workflow documentation
- **[Deployment Guide](DEPLOYMENT.md)** - Detailed deployment instructions
- **[Branch Protection Rules](.github/branch-protection-rules.md)** - Access control and workflow rules
- **[Oracle Instructions](ORACLE_INSTRUCTIONS.md)** - Oracle-specific setup and configuration

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Check service logs on Oracle instance
4. Open an issue in the repository
5. Contact repository owners for deployment issues

## 🎯 Roadmap

- [ ] Multi-tenant support
- [ ] Advanced analytics dashboard
- [ ] Machine learning model serving
- [ ] Real-time notifications
- [ ] Mobile application
- [ ] API rate limiting
- [ ] Advanced security features

---

**Built with ❤️ using Flask, Kafka, Airflow, and Oracle Cloud Infrastructure**
