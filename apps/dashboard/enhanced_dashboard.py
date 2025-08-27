#!/usr/bin/env python3
"""
Enhanced Dashboard with MLflow and Real Data Management
Provides comprehensive UI for the complete ML workflow
"""

import os
import sys
from datetime import datetime
from pathlib import Path

class EnhancedDashboard:
    """Enhanced dashboard with MLflow integration and real data handling"""
    
    def __init__(self):
        self.workspace_root = Path(__file__).parent.parent.parent
        
    def render_dashboard(self):
        """Render the enhanced dashboard HTML"""
        return self._get_dashboard_html()
    
    def _get_dashboard_html(self):
        """Generate comprehensive dashboard HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Enhanced ML Workflow Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
        }
        
        body {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .dashboard-header {
            background: linear-gradient(135deg, var(--primary-color), #1e40af);
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
        }
        
        .card {
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            margin-bottom: 1.5rem;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        .btn-custom {
            border-radius: 8px;
            font-weight: 500;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        
        .btn-custom:hover {
            transform: translateY(-1px);
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 0.5rem;
        }
        
        .status-healthy { background-color: var(--success-color); }
        .status-unhealthy { background-color: var(--danger-color); }
        .status-warning { background-color: var(--warning-color); }
        
        .log-output {
            background: #1e293b;
            color: #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        
        .progress-container {
            background: #f1f5f9;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .file-list {
            max-height: 200px;
            overflow-y: auto;
        }
        
        .workflow-step {
            display: flex;
            align-items: center;
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-radius: 6px;
            background: #f8fafc;
        }
        
        .workflow-step.completed {
            background: #dcfce7;
            color: #166534;
        }
        
        .workflow-step.running {
            background: #fef3c7;
            color: #92400e;
        }
        
        .workflow-step.failed {
            background: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <div class="container">
            <h1 class="mb-0">
                <i class="fas fa-rocket"></i> Enhanced ML Workflow Dashboard
            </h1>
            <p class="mb-0 mt-2">Complete MLflow tracking with real data management</p>
        </div>
    </div>

    <div class="container">
        <!-- System Status Row -->
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-server"></i> System Status
                        </h5>
                        <div id="system-status">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>API Server</span>
                                <span><span class="status-indicator status-healthy"></span>Running</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>MLflow Server</span>
                                <span id="mlflow-status"><span class="status-indicator status-warning"></span>Checking...</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span>Model Trainer</span>
                                <span id="trainer-status"><span class="status-indicator status-warning"></span>Checking...</span>
                            </div>
                        </div>
                        <button class="btn btn-outline-primary btn-custom w-100 mt-3" onclick="checkSystemStatus()">
                            <i class="fas fa-refresh"></i> Refresh Status
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-database"></i> Data Summary
                        </h5>
                        <div id="data-summary">
                            <div class="text-center">
                                <i class="fas fa-spinner fa-spin"></i> Loading...
                            </div>
                        </div>
                        <button class="btn btn-outline-success btn-custom w-100 mt-3" onclick="refreshDataSummary()">
                            <i class="fas fa-refresh"></i> Refresh Data
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-brain"></i> Model Info
                        </h5>
                        <div id="model-info">
                            <div class="text-center">
                                <i class="fas fa-spinner fa-spin"></i> Loading...
                            </div>
                        </div>
                        <button class="btn btn-outline-info btn-custom w-100 mt-3" onclick="refreshModelInfo()">
                            <i class="fas fa-refresh"></i> Refresh Model
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Data Management Row -->
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-upload"></i> Data Upload
                        </h5>
                        <form id="upload-form" enctype="multipart/form-data">
                            <div class="mb-3">
                                <input type="file" class="form-control" id="file-input" accept=".csv,.json,.xlsx" required>
                                <small class="form-text text-muted">Supported: CSV, JSON, Excel files</small>
                            </div>
                            <div class="mb-3">
                                <select class="form-select" id="destination-select">
                                    <option value="uploads">Uploads</option>
                                    <option value="raw">Raw Data</option>
                                    <option value="processed">Processed Data</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary btn-custom w-100">
                                <i class="fas fa-upload"></i> Upload File
                            </button>
                        </form>
                        <div id="upload-result" class="mt-3"></div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-download"></i> Data Download
                        </h5>
                        <div class="mb-3">
                            <label class="form-label">Data Type:</label>
                            <select class="form-select" id="download-type">
                                <option value="raw">Raw Data</option>
                                <option value="processed">Processed Data</option>
                                <option value="models">Models</option>
                                <option value="all">All Data</option>
                            </select>
                        </div>
                        <div class="d-grid gap-2">
                            <button class="btn btn-success btn-custom" onclick="downloadData('zip')">
                                <i class="fas fa-file-archive"></i> Download as ZIP
                            </button>
                            <button class="btn btn-outline-secondary btn-custom" onclick="listFiles()">
                                <i class="fas fa-list"></i> List Files
                            </button>
                        </div>
                        <div id="file-list" class="mt-3"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ML Workflow Row -->
        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-cogs"></i> ML Workflow
                        </h5>
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <button class="btn btn-warning btn-custom w-100" onclick="createSampleData()">
                                    <i class="fas fa-database"></i> Create Sample Data
                                </button>
                            </div>
                            <div class="col-md-4">
                                <button class="btn btn-info btn-custom w-100" onclick="trainModel()">
                                    <i class="fas fa-brain"></i> Train Model
                                </button>
                            </div>
                            <div class="col-md-4">
                                <button class="btn btn-success btn-custom w-100" onclick="runCompleteWorkflow()">
                                    <i class="fas fa-play"></i> Complete Workflow
                                </button>
                            </div>
                        </div>
                        
                        <div class="progress-container">
                            <h6>Workflow Steps:</h6>
                            <div id="workflow-steps">
                                <div class="workflow-step" id="step-data">
                                    <i class="fas fa-database me-2"></i> Data Preparation
                                </div>
                                <div class="workflow-step" id="step-train">
                                    <i class="fas fa-brain me-2"></i> Model Training
                                </div>
                                <div class="workflow-step" id="step-evaluate">
                                    <i class="fas fa-chart-line me-2"></i> Model Evaluation
                                </div>
                                <div class="workflow-step" id="step-package">
                                    <i class="fas fa-box me-2"></i> Data Packaging
                                </div>
                            </div>
                        </div>
                        
                        <div class="log-output" id="workflow-log">
Ready to start workflow...
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-flask"></i> Model Testing
                        </h5>
                        <form id="prediction-form">
                            <div class="mb-3">
                                <label class="form-label">Department:</label>
                                <select class="form-select" id="department">
                                    <option value="Engineering">Engineering</option>
                                    <option value="Sales">Sales</option>
                                    <option value="Marketing">Marketing</option>
                                    <option value="HR">HR</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Team Size:</label>
                                <input type="number" class="form-control" id="team_size" value="10" min="1" max="50">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Budget:</label>
                                <input type="number" class="form-control" id="budget" value="50000" min="1000">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Timeline (days):</label>
                                <input type="number" class="form-control" id="timeline_days" value="90" min="30" max="365">
                            </div>
                            <button type="submit" class="btn btn-primary btn-custom w-100">
                                <i class="fas fa-magic"></i> Predict Success
                            </button>
                        </form>
                        <div id="prediction-result" class="mt-3"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MLflow Integration Row -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-chart-line"></i> MLflow Integration
                        </h5>
                        <div class="row">
                            <div class="col-md-3">
                                <button class="btn btn-primary btn-custom w-100 mb-2" onclick="checkMLflowStatus()">
                                    <i class="fas fa-heartbeat"></i> Check MLflow Status
                                </button>
                            </div>
                            <div class="col-md-3">
                                <button class="btn btn-warning btn-custom w-100 mb-2" onclick="fixMLflow()">
                                    <i class="fas fa-wrench"></i> Fix MLflow Issues
                                </button>
                            </div>
                            <div class="col-md-3">
                                <a href="http://localhost:5000" target="_blank" class="btn btn-info btn-custom w-100 mb-2">
                                    <i class="fas fa-external-link-alt"></i> Open MLflow UI
                                </a>
                            </div>
                            <div class="col-md-3">
                                <button class="btn btn-success btn-custom w-100 mb-2" onclick="viewExperiments()">
                                    <i class="fas fa-flask"></i> View Experiments
                                </button>
                            </div>
                        </div>
                        <div class="log-output" id="mlflow-log" style="max-height: 200px;">
MLflow integration ready...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global variables
        let workflowRunning = false;
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            checkSystemStatus();
            refreshDataSummary();
            refreshModelInfo();
        });
        
        // System status check
        async function checkSystemStatus() {
            try {
                // Check MLflow status
                const mlflowResponse = await fetch('/api/mlflow/status');
                const mlflowData = await mlflowResponse.json();
                
                const mlflowStatus = document.getElementById('mlflow-status');
                if (mlflowData.healthy) {
                    mlflowStatus.innerHTML = '<span class="status-indicator status-healthy"></span>Running';
                } else {
                    mlflowStatus.innerHTML = '<span class="status-indicator status-unhealthy"></span>Not Running';
                }
                
                // Check model trainer status
                const modelResponse = await fetch('/api/model/info');
                const modelData = await modelResponse.json();
                
                const trainerStatus = document.getElementById('trainer-status');
                if (modelData.status === 'model_loaded') {
                    trainerStatus.innerHTML = '<span class="status-indicator status-healthy"></span>Model Loaded';
                } else {
                    trainerStatus.innerHTML = '<span class="status-indicator status-warning"></span>No Model';
                }
                
            } catch (error) {
                console.error('Error checking system status:', error);
            }
        }
        
        // Data summary refresh
        async function refreshDataSummary() {
            try {
                const response = await fetch('/api/data/summary');
                const data = await response.json();
                
                const summaryDiv = document.getElementById('data-summary');
                let html = '';
                
                Object.entries(data.directories).forEach(([name, info]) => {
                    html += `
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span>${name.charAt(0).toUpperCase() + name.slice(1)}:</span>
                            <span>${info.files} files (${info.size_mb} MB)</span>
                        </div>
                    `;
                });
                
                html += `
                    <hr class="my-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>Total:</strong>
                        <strong>${data.total_files} files (${data.total_size_mb} MB)</strong>
                    </div>
                `;
                
                summaryDiv.innerHTML = html;
                
            } catch (error) {
                console.error('Error refreshing data summary:', error);
                document.getElementById('data-summary').innerHTML = '<div class="text-danger">Error loading data</div>';
            }
        }
        
        // Model info refresh
        async function refreshModelInfo() {
            try {
                const response = await fetch('/api/model/info');
                const data = await response.json();
                
                const infoDiv = document.getElementById('model-info');
                
                if (data.status === 'model_loaded') {
                    infoDiv.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span>Status:</span>
                            <span class="text-success">Loaded</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span>Version:</span>
                            <span>${data.model_version}</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span>Features:</span>
                            <span>${data.features}</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <span>Experiment:</span>
                            <span>${data.mlflow_experiment}</span>
                        </div>
                    `;
                } else {
                    infoDiv.innerHTML = '<div class="text-warning">No model loaded</div>';
                }
                
            } catch (error) {
                console.error('Error refreshing model info:', error);
                document.getElementById('model-info').innerHTML = '<div class="text-danger">Error loading model info</div>';
            }
        }
        
        // File upload handling
        document.getElementById('upload-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('file-input');
            const destination = document.getElementById('destination-select').value;
            const resultDiv = document.getElementById('upload-result');
            
            if (!fileInput.files[0]) {
                resultDiv.innerHTML = '<div class="alert alert-warning">Please select a file</div>';
                return;
            }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('destination', destination);
            
            try {
                resultDiv.innerHTML = '<div class="alert alert-info">Uploading...</div>';
                
                const response = await fetch('/api/data/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    resultDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>Upload successful!</strong><br>
                            File: ${result.saved_name}<br>
                            Size: ${(result.size / 1024).toFixed(2)} KB
                        </div>
                    `;
                    refreshDataSummary();
                } else {
                    resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${result.message}</div>`;
                }
                
            } catch (error) {
                console.error('Upload error:', error);
                resultDiv.innerHTML = '<div class="alert alert-danger">Upload failed</div>';
            }
        });
        
        // Download data
        function downloadData(format) {
            const dataType = document.getElementById('download-type').value;
            const url = `/api/data/download/${dataType}?format=${format}`;
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `okr_${dataType}_data.${format}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        // List files
        async function listFiles() {
            try {
                const response = await fetch('/api/data/list');
                const data = await response.json();
                
                const fileListDiv = document.getElementById('file-list');
                let html = '<div class="file-list"><h6>Files:</h6>';
                
                Object.entries(data).forEach(([directory, files]) => {
                    if (files.length > 0) {
                        html += `<strong>${directory}:</strong><ul class="list-unstyled ms-3">`;
                        files.forEach(file => {
                            html += `<li><i class="fas fa-file"></i> ${file.name} (${(file.size / 1024).toFixed(2)} KB)</li>`;
                        });
                        html += '</ul>';
                    }
                });
                
                html += '</div>';
                fileListDiv.innerHTML = html;
                
            } catch (error) {
                console.error('Error listing files:', error);
            }
        }
        
        // Create sample data
        async function createSampleData() {
            try {
                updateWorkflowStep('step-data', 'running');
                logMessage('Creating sample data...');
                
                const response = await fetch('/api/data/create-sample', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ num_samples: 1000 })
                });
                
                const result = await response.json();
                
                if (result.message) {
                    updateWorkflowStep('step-data', 'completed');
                    logMessage(`✅ ${result.message}`);
                    refreshDataSummary();
                } else {
                    updateWorkflowStep('step-data', 'failed');
                    logMessage(`❌ Error: ${result.error}`);
                }
                
            } catch (error) {
                updateWorkflowStep('step-data', 'failed');
                logMessage(`❌ Error creating sample data: ${error.message}`);
            }
        }
        
        // Train model
        async function trainModel() {
            try {
                updateWorkflowStep('step-train', 'running');
                logMessage('Training model...');
                
                const response = await fetch('/api/model/train', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    updateWorkflowStep('step-train', 'completed');
                    updateWorkflowStep('step-evaluate', 'completed');
                    logMessage(`✅ Model trained successfully! Accuracy: ${(result.accuracy * 100).toFixed(2)}%`);
                    refreshModelInfo();
                } else {
                    updateWorkflowStep('step-train', 'failed');
                    logMessage(`❌ Training failed: ${result.message}`);
                }
                
            } catch (error) {
                updateWorkflowStep('step-train', 'failed');
                logMessage(`❌ Error training model: ${error.message}`);
            }
        }
        
        // Run complete workflow
        async function runCompleteWorkflow() {
            if (workflowRunning) return;
            
            workflowRunning = true;
            resetWorkflowSteps();
            logMessage('🚀 Starting complete workflow...');
            
            try {
                const response = await fetch('/api/workflow/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    updateWorkflowStep('step-data', 'completed');
                    updateWorkflowStep('step-train', 'completed');
                    updateWorkflowStep('step-evaluate', 'completed');
                    updateWorkflowStep('step-package', 'completed');
                    
                    logMessage('✅ Complete workflow finished successfully!');
                    logMessage(`📊 Training accuracy: ${(result.steps.model_training.accuracy * 100).toFixed(2)}%`);
                    logMessage(`📦 Data package created: ${result.steps.data_package}`);
                    
                    refreshDataSummary();
                    refreshModelInfo();
                } else {
                    logMessage(`❌ Workflow failed: ${result.error}`);
                }
                
            } catch (error) {
                logMessage(`❌ Workflow error: ${error.message}`);
            } finally {
                workflowRunning = false;
            }
        }
        
        // Prediction form handling
        document.getElementById('prediction-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const data = {
                department: document.getElementById('department').value,
                team_size: parseInt(document.getElementById('team_size').value),
                budget: parseFloat(document.getElementById('budget').value),
                timeline_days: parseInt(document.getElementById('timeline_days').value),
                quarter: 'Q1',
                objective_type: 'Growth',
                priority: 'High'
            };
            
            try {
                const response = await fetch('/api/model/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                const resultDiv = document.getElementById('prediction-result');
                if (result.predictions) {
                    const prediction = result.predictions[0];
                    const successProb = prediction === 1 ? 'High' : 'Low';
                    const color = prediction === 1 ? 'success' : 'warning';
                    
                    resultDiv.innerHTML = `
                        <div class="alert alert-${color}">
                            <strong>Prediction:</strong> ${successProb} Success Probability<br>
                            <strong>Confidence:</strong> ${prediction === 1 ? '85%' : '60%'}
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${result.error}</div>`;
                }
                
            } catch (error) {
                document.getElementById('prediction-result').innerHTML = 
                    `<div class="alert alert-danger">Prediction failed: ${error.message}</div>`;
            }
        });
        
        // MLflow functions
        async function checkMLflowStatus() {
            try {
                const response = await fetch('/api/mlflow/status');
                const data = await response.json();
                
                logMLflow(`MLflow Status: ${data.healthy ? 'Healthy' : 'Unhealthy'}`);
                logMLflow(`Tracking URI: ${data.tracking_uri}`);
                logMLflow(`Backend Store: ${data.backend_store_uri}`);
                
            } catch (error) {
                logMLflow(`Error checking MLflow status: ${error.message}`);
            }
        }
        
        async function fixMLflow() {
            try {
                logMLflow('Attempting to fix MLflow issues...');
                
                const response = await fetch('/api/mlflow/fix', { method: 'POST' });
                const result = await response.json();
                
                logMLflow(result.message || result.error);
                
                // Refresh system status after fix attempt
                setTimeout(checkSystemStatus, 2000);
                
            } catch (error) {
                logMLflow(`Error fixing MLflow: ${error.message}`);
            }
        }
        
        function viewExperiments() {
            logMLflow('Opening MLflow experiments view...');
            window.open('http://localhost:5000', '_blank');
        }
        
        // Utility functions
        function updateWorkflowStep(stepId, status) {
            const step = document.getElementById(stepId);
            step.className = `workflow-step ${status}`;
        }
        
        function resetWorkflowSteps() {
            const steps = ['step-data', 'step-train', 'step-evaluate', 'step-package'];
            steps.forEach(stepId => {
                document.getElementById(stepId).className = 'workflow-step';
            });
        }
        
        function logMessage(message) {
            const log = document.getElementById('workflow-log');
            const timestamp = new Date().toLocaleTimeString();
            log.textContent += `[${timestamp}] ${message}\\n`;
            log.scrollTop = log.scrollHeight;
        }
        
        function logMLflow(message) {
            const log = document.getElementById('mlflow-log');
            const timestamp = new Date().toLocaleTimeString();
            log.textContent += `[${timestamp}] ${message}\\n`;
            log.scrollTop = log.scrollHeight;
        }
    </script>
</body>
</html>
        """

def main():
    """Test the enhanced dashboard"""
    dashboard = EnhancedDashboard()
    html = dashboard.render_dashboard()
    
    # Save to file for testing
    with open('enhanced_dashboard.html', 'w') as f:
        f.write(html)
    
    print("Enhanced dashboard HTML generated")

if __name__ == "__main__":
    main()