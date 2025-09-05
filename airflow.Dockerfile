FROM apache/airflow:2.7.3-python3.10

# Switch to root user to install system dependencies
USER root

# Install system dependencies including Oracle client
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        default-libmysqlclient-dev \
        freetds-dev \
        freetds-bin \
        libaio1 \
        libffi-dev \
        libkrb5-dev \
        libsasl2-dev \
        libsasl2-modules \
        libssl-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libxmlsec1-openssl \
        libxslt1-dev \
        libldap2-dev \
        pkg-config \
        sasl2-bin \
        unixodbc-dev \
        vim \
        wget \
        unzip \
        netcat-openbsd \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Oracle Instant Client
RUN mkdir -p /opt/oracle \
    && cd /opt/oracle \
    && wget https://download.oracle.com/otn_software/linux/instantclient/1923000/instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && wget https://download.oracle.com/otn_software/linux/instantclient/1923000/instantclient-devel-linux.x64-19.23.0.0.0dbru.zip \
    && unzip instantclient-basic-linux.x64-19.23.0.0.0dbru.zip \
    && unzip instantclient-devel-linux.x64-19.23.0.0.0dbru.zip \
    && rm -f *.zip \
    && cd instantclient_19_23 \
    && echo /opt/oracle/instantclient_19_23 > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

# Set Oracle environment variables
ENV ORACLE_HOME=/opt/oracle/instantclient_19_23
ENV LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
ENV PATH=$ORACLE_HOME:$PATH

# Switch back to airflow user
USER airflow

# Copy requirements file
COPY requirements.txt /requirements.txt
COPY requirements-scm.txt /requirements-scm.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /requirements.txt \
    && pip install --no-cache-dir -r /requirements-scm.txt

# Ensure airflow is properly installed and accessible
RUN pip install --no-cache-dir --force-reinstall apache-airflow[postgres,redis,celery]==2.7.3

# Ensure airflow is in PATH
ENV PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"

# Create symlinks to ensure airflow is accessible from multiple locations
RUN mkdir -p /usr/local/bin \
    && ln -sf /home/airflow/.local/bin/airflow /usr/local/bin/airflow || true \
    && ln -sf /home/airflow/.local/bin/airflow /usr/bin/airflow || true

# Verify airflow installation
RUN which airflow || echo "Airflow not in PATH" \
    && ls -la /home/airflow/.local/bin/airflow || echo "Airflow binary not found" \
    && /home/airflow/.local/bin/airflow version || echo "Airflow version check failed"

# Set environment variables
ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=True
ENV AIRFLOW__API__AUTH_BACKEND=airflow.api.auth.backend.basic_auth
ENV AIRFLOW__CORE__ENABLE_XCOM_PICKLING=True

# Create necessary directories
RUN mkdir -p /opt/airflow/data/scm_output/final \
    && mkdir -p /opt/airflow/data/okr_output/final \
    && mkdir -p /opt/airflow/data/models/scm \
    && mkdir -p /opt/airflow/data/models/okr \
    && mkdir -p /opt/airflow/logs

# Set working directory
WORKDIR /opt/airflow

# Expose port
EXPOSE 8080