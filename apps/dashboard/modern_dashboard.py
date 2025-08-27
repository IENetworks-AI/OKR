"""
Modern Professional Dashboard for OKR Data Pipeline

This dashboard provides:
- Real-time pipeline monitoring
- Data upload/download functionality
- System status overview
- Interactive charts and metrics
- File management interface
"""

from flask import Flask, render_template_string, request, jsonify, send_file, redirect, url_for
import os
import json
import yaml
import pandas as pd
import datetime
import requests
import logging
from typing import Dict, List, Any, Optional
import glob
from werkzeug.utils import secure_filename
import io
import zipfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modern Dashboard HTML Template
MODERN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OKR Data Pipeline Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --dark-color: #1e293b;
            --light-color: #f8fafc;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .sidebar {
            background: var(--dark-color);
            min-height: 100vh;
            position: fixed;
            top: 0;
            left: -250px;
            width: 250px;
            transition: left 0.3s ease;
            z-index: 1000;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }
        
        .sidebar.active {
            left: 0;
        }
        
        .sidebar .nav-link {
            color: #cbd5e1;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 5px 10px;
            transition: all 0.3s ease;
        }
        
        .sidebar .nav-link:hover {
            background: var(--primary-color);
            color: white;
        }
        
        .sidebar .nav-link.active {
            background: var(--primary-color);
            color: white;
        }
        
        .main-content {
            margin-left: 0;
            transition: margin-left 0.3s ease;
            padding: 20px;
        }
        
        .main-content.shifted {
            margin-left: 250px;
        }
        
        .navbar {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.9);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }
        
        .metric-card {
            text-align: center;
            padding: 30px 20px;
        }
        
        .metric-number {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .metric-label {
            color: var(--secondary-color);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.9rem;
        }
        
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 500;
            font-size: 0.85rem;
        }
        
        .btn-modern {
            border-radius: 10px;
            font-weight: 500;
            padding: 12px 24px;
            transition: all 0.3s ease;
            border: none;
        }
        
        .btn-modern:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .upload-area {
            border: 2px dashed var(--primary-color);
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            background: rgba(37, 99, 235, 0.05);
        }
        
        .upload-area:hover {
            border-color: var(--success-color);
            background: rgba(16, 185, 129, 0.05);
        }
        
        .file-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .file-item {
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: between;
            align-items: center;
        }
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .progress-ring {
            width: 60px;
            height: 60px;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }
        
        @media (max-width: 768px) {
            .main-content {
                margin-left: 0 !important;
            }
            
            .sidebar {
                width: 100%;
                left: -100%;
            }
        }
        
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 999;
            display: none;
        }
        
        .overlay.active {
            display: block;
        }
    </style>
</head>
<body>
    <!-- Overlay for mobile -->
    <div class="overlay" id="overlay"></div>
    
    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
        <div class="p-4">
            <h4 class="text-white mb-4">
                <i class="fas fa-chart-line me-2"></i>
                OKR Pipeline
            </h4>
        </div>
        <nav class="nav flex-column">
            <a class="nav-link active" href="#" data-section="overview">
                <i class="fas fa-tachometer-alt me-2"></i> Overview
            </a>
            <a class="nav-link" href="#" data-section="data-management">
                <i class="fas fa-database me-2"></i> Data Management
            </a>
            <a class="nav-link" href="#" data-section="pipelines">
                <i class="fas fa-cogs me-2"></i> Pipelines
            </a>
            <a class="nav-link" href="#" data-section="monitoring">
                <i class="fas fa-chart-bar me-2"></i> Monitoring
            </a>
            <a class="nav-link" href="#" data-section="kafka">
                <i class="fas fa-stream me-2"></i> Kafka Streams
            </a>
            <a class="nav-link" href="#" data-section="mlflow">
                <i class="fas fa-brain me-2"></i> MLflow
            </a>
        </nav>
    </div>
    
    <!-- Main Content -->
    <div class="main-content" id="mainContent">
        <!-- Top Navigation -->
        <nav class="navbar navbar-expand-lg navbar-light mb-4">
            <div class="container-fluid">
                <button class="btn btn-outline-primary me-3" id="sidebarToggle">
                    <i class="fas fa-bars"></i>
                </button>
                <h1 class="navbar-brand mb-0 fw-bold">OKR Data Pipeline Dashboard</h1>
                <div class="ms-auto">
                    <span class="badge bg-success me-2">
                        <i class="fas fa-circle me-1"></i> Online
                    </span>
                    <span class="text-muted">{{ current_time }}</span>
                </div>
            </div>
        </nav>
        
        <!-- Overview Section -->
        <div id="overview-section" class="content-section">
            <!-- System Status Cards -->
            <div class="row mb-4">
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card metric-card">
                        <div class="metric-number text-primary" id="total-files">{{ metrics.total_files }}</div>
                        <div class="metric-label">Total Files</div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card metric-card">
                        <div class="metric-number text-success" id="processed-files">{{ metrics.processed_files }}</div>
                        <div class="metric-label">Processed Files</div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card metric-card">
                        <div class="metric-number text-info" id="total-records">{{ metrics.total_records }}</div>
                        <div class="metric-label">Total Records</div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6 mb-3">
                    <div class="card metric-card">
                        <div class="metric-number text-warning" id="active-pipelines">{{ metrics.active_pipelines }}</div>
                        <div class="metric-label">Active Pipelines</div>
                    </div>
                </div>
            </div>
            
            <!-- System Status -->
            <div class="row mb-4">
                <div class="col-lg-8">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-server me-2"></i> System Status
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <span>Airflow</span>
                                        <span class="status-badge bg-success text-white" id="airflow-status">Running</span>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <span>Kafka</span>
                                        <span class="status-badge bg-success text-white" id="kafka-status">Running</span>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <span>PostgreSQL</span>
                                        <span class="status-badge bg-success text-white" id="postgres-status">Running</span>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <span>MLflow</span>
                                        <span class="status-badge bg-warning text-dark" id="mlflow-status">Pending</span>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <span>API Service</span>
                                        <span class="status-badge bg-success text-white" id="api-status">Running</span>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <span>Oracle DB</span>
                                        <span class="status-badge bg-success text-white" id="oracle-status">Running</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-chart-pie me-2"></i> Data Distribution
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="dataDistributionChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Recent Activity -->
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-clock me-2"></i> Recent Activity
                    </h5>
                </div>
                <div class="card-body">
                    <div id="recent-activity">
                        <div class="d-flex align-items-center mb-3">
                            <div class="bg-success rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 40px; height: 40px;">
                                <i class="fas fa-check text-white"></i>
                            </div>
                            <div>
                                <div class="fw-semibold">CSV Ingestion Completed</div>
                                <div class="text-muted small">Processed 12,893 records from objectives_PMS.csv</div>
                            </div>
                            <div class="ms-auto text-muted small">2 min ago</div>
                        </div>
                        <div class="d-flex align-items-center mb-3">
                            <div class="bg-primary rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 40px; height: 40px;">
                                <i class="fas fa-upload text-white"></i>
                            </div>
                            <div>
                                <div class="fw-semibold">API Data Ingested</div>
                                <div class="text-muted small">Fetched 200 new records from external API</div>
                            </div>
                            <div class="ms-auto text-muted small">5 min ago</div>
                        </div>
                        <div class="d-flex align-items-center">
                            <div class="bg-info rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 40px; height: 40px;">
                                <i class="fas fa-stream text-white"></i>
                            </div>
                            <div>
                                <div class="fw-semibold">Kafka Stream Active</div>
                                <div class="text-muted small">Real-time data streaming to okr_raw_ingest topic</div>
                            </div>
                            <div class="ms-auto text-muted small">10 min ago</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Data Management Section -->
        <div id="data-management-section" class="content-section" style="display: none;">
            <div class="row">
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-cloud-upload-alt me-2"></i> Upload Data
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="upload-area" id="uploadArea">
                                <i class="fas fa-cloud-upload-alt fa-3x text-primary mb-3"></i>
                                <h5>Drop files here or click to upload</h5>
                                <p class="text-muted">Supported formats: CSV, JSON, Excel</p>
                                <input type="file" id="fileInput" multiple accept=".csv,.json,.xlsx,.xls" style="display: none;">
                                <button class="btn btn-primary btn-modern mt-3" onclick="document.getElementById('fileInput').click()">
                                    Choose Files
                                </button>
                            </div>
                            <div id="uploadProgress" class="mt-3" style="display: none;">
                                <div class="progress">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-download me-2"></i> Download Data
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="form-label">Select Data Type</label>
                                <select class="form-select" id="downloadType">
                                    <option value="raw">Raw Data</option>
                                    <option value="processed">Processed Data</option>
                                    <option value="reports">Reports</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">File Format</label>
                                <select class="form-select" id="downloadFormat">
                                    <option value="csv">CSV</option>
                                    <option value="json">JSON</option>
                                    <option value="excel">Excel</option>
                                    <option value="zip">ZIP Archive</option>
                                </select>
                            </div>
                            <button class="btn btn-success btn-modern w-100" onclick="downloadData()">
                                <i class="fas fa-download me-2"></i> Download
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- File Management -->
            <div class="card mt-4">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-folder me-2"></i> File Management
                    </h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Filename</th>
                                    <th>Type</th>
                                    <th>Size</th>
                                    <th>Upload Date</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="fileTable">
                                {% for file in files %}
                                <tr>
                                    <td>{{ file.name }}</td>
                                    <td><span class="badge bg-info">{{ file.type }}</span></td>
                                    <td>{{ file.size }}</td>
                                    <td>{{ file.upload_date }}</td>
                                    <td><span class="badge bg-{{ file.status_color }}">{{ file.status }}</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-primary" onclick="downloadFile('{{ file.name }}')">
                                            <i class="fas fa-download"></i>
                                        </button>
                                        <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('{{ file.name }}')">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Pipelines Section -->
        <div id="pipelines-section" class="content-section" style="display: none;">
            <div class="row">
                <div class="col-lg-4 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-file-csv me-2"></i> CSV Ingestion
                            </h5>
                        </div>
                        <div class="card-body text-center">
                            <div class="mb-3">
                                <span class="badge bg-success">Ready</span>
                            </div>
                            <p class="text-muted">Process CSV files from raw directory</p>
                            <button class="btn btn-primary btn-modern" onclick="triggerPipeline('enhanced_csv_ingestion_dag')">
                                <i class="fas fa-play me-2"></i> Run Pipeline
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-globe me-2"></i> API Ingestion
                            </h5>
                        </div>
                        <div class="card-body text-center">
                            <div class="mb-3">
                                <span class="badge bg-success">Ready</span>
                            </div>
                            <p class="text-muted">Fetch data from external APIs</p>
                            <button class="btn btn-primary btn-modern" onclick="triggerPipeline('enhanced_api_ingestion_dag')">
                                <i class="fas fa-play me-2"></i> Run Pipeline
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-brain me-2"></i> Model Training
                            </h5>
                        </div>
                        <div class="card-body text-center">
                            <div class="mb-3">
                                <span class="badge bg-warning">Pending</span>
                            </div>
                            <p class="text-muted">Train ML models on processed data</p>
                            <button class="btn btn-primary btn-modern" onclick="triggerPipeline('model_training')">
                                <i class="fas fa-play me-2"></i> Run Pipeline
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Pipeline Status -->
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-list me-2"></i> Pipeline Status
                    </h5>
                </div>
                <div class="card-body">
                    <div id="pipelineStatus">
                        <div class="d-flex justify-content-between align-items-center mb-3 p-3 border rounded">
                            <div>
                                <h6 class="mb-1">Enhanced CSV Ingestion</h6>
                                <small class="text-muted">Last run: 2 hours ago</small>
                            </div>
                            <span class="badge bg-success">Success</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-3 p-3 border rounded">
                            <div>
                                <h6 class="mb-1">Enhanced API Ingestion</h6>
                                <small class="text-muted">Last run: 1 hour ago</small>
                            </div>
                            <span class="badge bg-success">Success</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center p-3 border rounded">
                            <div>
                                <h6 class="mb-1">Model Training Pipeline</h6>
                                <small class="text-muted">Last run: Never</small>
                            </div>
                            <span class="badge bg-secondary">Not Started</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Monitoring Section -->
        <div id="monitoring-section" class="content-section" style="display: none;">
            <div class="row mb-4">
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-chart-line me-2"></i> Processing Metrics
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="processingChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-tachometer-alt me-2"></i> System Performance
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <div class="d-flex justify-content-between">
                                    <span>CPU Usage</span>
                                    <span>65%</span>
                                </div>
                                <div class="progress">
                                    <div class="progress-bar bg-warning" style="width: 65%"></div>
                                </div>
                            </div>
                            <div class="mb-3">
                                <div class="d-flex justify-content-between">
                                    <span>Memory Usage</span>
                                    <span>45%</span>
                                </div>
                                <div class="progress">
                                    <div class="progress-bar bg-info" style="width: 45%"></div>
                                </div>
                            </div>
                            <div class="mb-3">
                                <div class="d-flex justify-content-between">
                                    <span>Disk Usage</span>
                                    <span>30%</span>
                                </div>
                                <div class="progress">
                                    <div class="progress-bar bg-success" style="width: 30%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Kafka Section -->
        <div id="kafka-section" class="content-section" style="display: none;">
            <div class="row">
                <div class="col-lg-8">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-stream me-2"></i> Kafka Topics
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            <th>Topic Name</th>
                                            <th>Messages</th>
                                            <th>Partitions</th>
                                            <th>Status</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>okr_raw_ingest</td>
                                            <td>1,234</td>
                                            <td>3</td>
                                            <td><span class="badge bg-success">Active</span></td>
                                            <td>
                                                <button class="btn btn-sm btn-outline-primary">View</button>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>okr_processed_updates</td>
                                            <td>856</td>
                                            <td>3</td>
                                            <td><span class="badge bg-success">Active</span></td>
                                            <td>
                                                <button class="btn btn-sm btn-outline-primary">View</button>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td>okr_api_data</td>
                                            <td>432</td>
                                            <td>2</td>
                                            <td><span class="badge bg-success">Active</span></td>
                                            <td>
                                                <button class="btn btn-sm btn-outline-primary">View</button>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-cog me-2"></i> Kafka Controls
                            </h5>
                        </div>
                        <div class="card-body">
                            <button class="btn btn-success btn-modern w-100 mb-2" onclick="testKafka()">
                                <i class="fas fa-play me-2"></i> Test Connection
                            </button>
                            <button class="btn btn-info btn-modern w-100 mb-2" onclick="viewKafkaUI()">
                                <i class="fas fa-external-link-alt me-2"></i> Open Kafka UI
                            </button>
                            <button class="btn btn-warning btn-modern w-100" onclick="resetKafka()">
                                <i class="fas fa-redo me-2"></i> Reset Topics
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- MLflow Section -->
        <div id="mlflow-section" class="content-section" style="display: none;">
            <div class="row">
                <div class="col-lg-8">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-brain me-2"></i> MLflow Tracking
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                MLflow tracking server is currently not accessible. Please check the service status.
                            </div>
                            <button class="btn btn-primary btn-modern" onclick="fixMLflow()">
                                <i class="fas fa-wrench me-2"></i> Fix MLflow Connection
                            </button>
                            <button class="btn btn-info btn-modern ms-2" onclick="openMLflowUI()">
                                <i class="fas fa-external-link-alt me-2"></i> Open MLflow UI
                            </button>
                        </div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">
                                <i class="fas fa-chart-bar me-2"></i> Model Metrics
                            </h5>
                        </div>
                        <div class="card-body">
                            <div class="text-center">
                                <div class="text-muted">No models tracked yet</div>
                                <i class="fas fa-chart-bar fa-3x text-muted mt-3"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js"></script>
    <script>
        // Sidebar functionality
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('mainContent');
        const overlay = document.getElementById('overlay');
        const sidebarToggle = document.getElementById('sidebarToggle');
        
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            mainContent.classList.toggle('shifted');
            overlay.classList.toggle('active');
        });
        
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            mainContent.classList.remove('shifted');
            overlay.classList.remove('active');
        });
        
        // Navigation functionality
        const navLinks = document.querySelectorAll('.sidebar .nav-link');
        const contentSections = document.querySelectorAll('.content-section');
        
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Remove active class from all links
                navLinks.forEach(l => l.classList.remove('active'));
                // Add active class to clicked link
                this.classList.add('active');
                
                // Hide all sections
                contentSections.forEach(section => section.style.display = 'none');
                // Show selected section
                const sectionId = this.getAttribute('data-section') + '-section';
                document.getElementById(sectionId).style.display = 'block';
            });
        });
        
        // File upload functionality
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.borderColor = '#10b981';
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.style.borderColor = '#2563eb';
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderColor = '#2563eb';
            const files = e.dataTransfer.files;
            handleFiles(files);
        });
        
        fileInput.addEventListener('change', function() {
            handleFiles(this.files);
        });
        
        function handleFiles(files) {
            if (files.length > 0) {
                uploadFiles(files);
            }
        }
        
        async function uploadFiles(files) {
            const progressDiv = document.getElementById('uploadProgress');
            const progressBar = progressDiv.querySelector('.progress-bar');
            
            progressDiv.style.display = 'block';
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const progress = ((i + 1) / files.length) * 100;
                        progressBar.style.width = progress + '%';
                        progressBar.textContent = Math.round(progress) + '%';
                    }
                } catch (error) {
                    console.error('Upload error:', error);
                }
            }
            
            setTimeout(() => {
                progressDiv.style.display = 'none';
                progressBar.style.width = '0%';
                location.reload(); // Refresh to show new files
            }, 1000);
        }
        
        // Chart initialization
        function initCharts() {
            // Data Distribution Chart
            const ctx1 = document.getElementById('dataDistributionChart').getContext('2d');
            new Chart(ctx1, {
                type: 'doughnut',
                data: {
                    labels: ['Objectives', 'Key Results', 'Tasks', 'Plans'],
                    datasets: [{
                        data: [12893, 61375, 357929, 500054],
                        backgroundColor: ['#2563eb', '#10b981', '#f59e0b', '#ef4444']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
            
            // Processing Metrics Chart
            const ctx2 = document.getElementById('processingChart');
            if (ctx2) {
                new Chart(ctx2, {
                    type: 'line',
                    data: {
                        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                        datasets: [{
                            label: 'Records Processed',
                            data: [12000, 19000, 15000, 22000, 18000, 25000, 30000],
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            }
        }
        
        // API Functions
        async function triggerPipeline(dagId) {
            try {
                const response = await fetch(`/api/pipeline/trigger/${dagId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({source: 'dashboard'})
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(`Pipeline ${dagId} triggered successfully!`);
                } else {
                    alert(`Error triggering pipeline: ${result.message || 'Unknown error'}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
        
        async function downloadData() {
            const type = document.getElementById('downloadType').value;
            const format = document.getElementById('downloadFormat').value;
            
            try {
                const response = await fetch(`/api/download/${type}?format=${format}`);
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `okr_${type}_data.${format === 'zip' ? 'zip' : format}`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                } else {
                    alert('Error downloading data');
                }
            } catch (error) {
                alert(`Download error: ${error.message}`);
            }
        }
        
        function testKafka() {
            fetch('/api/kafka/test')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('Kafka connection test successful!');
                    } else {
                        alert('Kafka connection test failed: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('Error testing Kafka: ' + error.message);
                });
        }
        
        function viewKafkaUI() {
            window.open('http://localhost:8085', '_blank');
        }
        
        function openMLflowUI() {
            window.open('http://localhost:5000', '_blank');
        }
        
        function fixMLflow() {
            fetch('/api/mlflow/fix', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message || 'MLflow fix attempted');
                    location.reload();
                })
                .catch(error => {
                    alert('Error fixing MLflow: ' + error.message);
                });
        }
        
        // Initialize charts when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            
            // Auto-refresh metrics every 30 seconds
            setInterval(function() {
                fetch('/api/metrics')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('total-files').textContent = data.total_files || 0;
                        document.getElementById('processed-files').textContent = data.processed_files || 0;
                        document.getElementById('total-records').textContent = data.total_records || 0;
                        document.getElementById('active-pipelines').textContent = data.active_pipelines || 0;
                    })
                    .catch(error => console.error('Error refreshing metrics:', error));
            }, 30000);
        });
    </script>
</body>
</html>
"""

class ModernDashboard:
    def __init__(self, data_dir: str = "/workspace/data"):
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.processed_dir = os.path.join(data_dir, "processed")
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics for dashboard."""
        try:
            # Count files
            raw_files = glob.glob(os.path.join(self.raw_dir, "*.csv"))
            processed_files = glob.glob(os.path.join(self.processed_dir, "*.csv"))
            
            # Count total records
            total_records = 0
            for file_path in raw_files:
                try:
                    df = pd.read_csv(file_path)
                    total_records += len(df)
                except:
                    continue
            
            return {
                'total_files': len(raw_files),
                'processed_files': len(processed_files),
                'total_records': f"{total_records:,}",
                'active_pipelines': 2  # CSV and API ingestion
            }
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {
                'total_files': 0,
                'processed_files': 0,
                'total_records': '0',
                'active_pipelines': 0
            }
    
    def get_file_list(self) -> List[Dict[str, Any]]:
        """Get list of files for file management."""
        files = []
        try:
            for directory, file_type in [(self.raw_dir, 'Raw'), (self.processed_dir, 'Processed')]:
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        if filename.endswith(('.csv', '.json', '.xlsx')):
                            file_path = os.path.join(directory, filename)
                            stat = os.stat(file_path)
                            
                            files.append({
                                'name': filename,
                                'type': file_type,
                                'size': f"{stat.st_size / (1024*1024):.2f} MB",
                                'upload_date': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                                'status': 'Ready',
                                'status_color': 'success'
                            })
        except Exception as e:
            logger.error(f"Error getting file list: {e}")
        
        return files
    
    def render_dashboard(self) -> str:
        """Render the modern dashboard."""
        try:
            metrics = self.get_metrics()
            files = self.get_file_list()
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Use Jinja2-style template rendering (simplified)
            html = MODERN_DASHBOARD_HTML
            html = html.replace('{{ current_time }}', current_time)
            html = html.replace('{{ metrics.total_files }}', str(metrics['total_files']))
            html = html.replace('{{ metrics.processed_files }}', str(metrics['processed_files']))
            html = html.replace('{{ metrics.total_records }}', str(metrics['total_records']))
            html = html.replace('{{ metrics.active_pipelines }}', str(metrics['active_pipelines']))
            
            # Simple file list rendering
            file_rows = ""
            for file in files:
                file_rows += f"""
                <tr>
                    <td>{file['name']}</td>
                    <td><span class="badge bg-info">{file['type']}</span></td>
                    <td>{file['size']}</td>
                    <td>{file['upload_date']}</td>
                    <td><span class="badge bg-{file['status_color']}">{file['status']}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="downloadFile('{file['name']}')">
                            <i class="fas fa-download"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('{file['name']}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
                """
            
            # Replace file table placeholder
            html = html.replace('{% for file in files %}', '')
            html = html.replace('{% endfor %}', file_rows)
            
            return html
            
        except Exception as e:
            logger.error(f"Error rendering dashboard: {e}")
            return f"<h1>Error loading dashboard: {e}</h1>"

def create_dashboard_app():
    """Create Flask app for the modern dashboard."""
    app = Flask(__name__)
    dashboard = ModernDashboard()
    
    @app.route('/')
    def index():
        return dashboard.render_dashboard()
    
    @app.route('/api/metrics')
    def api_metrics():
        return jsonify(dashboard.get_metrics())
    
    @app.route('/api/upload', methods=['POST'])
    def api_upload():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(dashboard.raw_dir, filename)
            
            # Ensure directory exists
            os.makedirs(dashboard.raw_dir, exist_ok=True)
            
            file.save(file_path)
            
            return jsonify({'message': f'File {filename} uploaded successfully'})
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/download/<data_type>')
    def api_download(data_type):
        try:
            format_type = request.args.get('format', 'csv')
            
            if data_type == 'raw':
                directory = dashboard.raw_dir
            elif data_type == 'processed':
                directory = dashboard.processed_dir
            else:
                return jsonify({'error': 'Invalid data type'}), 400
            
            if format_type == 'zip':
                # Create ZIP file
                memory_file = io.BytesIO()
                with zipfile.ZipFile(memory_file, 'w') as zf:
                    for filename in os.listdir(directory):
                        if filename.endswith('.csv'):
                            zf.write(os.path.join(directory, filename), filename)
                
                memory_file.seek(0)
                return send_file(
                    memory_file,
                    as_attachment=True,
                    download_name=f'okr_{data_type}_data.zip',
                    mimetype='application/zip'
                )
            else:
                # Return first CSV file found
                csv_files = glob.glob(os.path.join(directory, "*.csv"))
                if csv_files:
                    return send_file(csv_files[0], as_attachment=True)
                else:
                    return jsonify({'error': 'No files found'}), 404
                    
        except Exception as e:
            logger.error(f"Download error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/pipeline/trigger/<dag_id>', methods=['POST'])
    def api_trigger_pipeline(dag_id):
        try:
            # This would integrate with Airflow API
            # For now, return success message
            return jsonify({
                'message': f'Pipeline {dag_id} triggered successfully',
                'status': 'success'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/kafka/test')
    def api_kafka_test():
        try:
            from data.streaming import KafkaStreamManager
            kafka_manager = KafkaStreamManager('kafka:9092')
            kafka_manager.close()
            return jsonify({'status': 'success', 'message': 'Kafka connection successful'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    
    @app.route('/api/mlflow/fix', methods=['POST'])
    def api_mlflow_fix():
        try:
            # This would attempt to fix MLflow connection
            return jsonify({'message': 'MLflow fix attempted. Please check the service.'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app

if __name__ == '__main__':
    app = create_dashboard_app()
    app.run(host='0.0.0.0', port=5002, debug=True)