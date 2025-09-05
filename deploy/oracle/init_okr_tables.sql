-- OKR Database Schema Initialization
-- This script creates the necessary tables for OKR data storage

-- Create objectives table
CREATE TABLE objectives (
    objective_id NUMBER PRIMARY KEY,
    title VARCHAR2(500) NOT NULL,
    description CLOB,
    owner_id VARCHAR2(100),
    department VARCHAR2(100),
    quarter NUMBER(1) CHECK (quarter IN (1, 2, 3, 4)),
    year NUMBER(4),
    status VARCHAR2(50) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'on_hold')),
    priority VARCHAR2(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_date DATE DEFAULT SYSDATE,
    updated_date DATE DEFAULT SYSDATE,
    target_completion_date DATE
);

-- Create key_results table
CREATE TABLE key_results (
    key_result_id NUMBER PRIMARY KEY,
    objective_id NUMBER NOT NULL,
    title VARCHAR2(500) NOT NULL,
    description CLOB,
    metric_type VARCHAR2(50) DEFAULT 'percentage' CHECK (metric_type IN ('percentage', 'number', 'currency', 'boolean')),
    target_value NUMBER,
    current_value NUMBER DEFAULT 0,
    unit VARCHAR2(50),
    status VARCHAR2(50) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'on_hold')),
    progress_percentage NUMBER(5,2) DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    created_date DATE DEFAULT SYSDATE,
    updated_date DATE DEFAULT SYSDATE,
    due_date DATE,
    CONSTRAINT fk_kr_objective FOREIGN KEY (objective_id) REFERENCES objectives(objective_id)
);

-- Create progress_updates table
CREATE TABLE progress_updates (
    update_id NUMBER PRIMARY KEY,
    key_result_id NUMBER NOT NULL,
    objective_id NUMBER NOT NULL,
    update_value NUMBER,
    progress_percentage NUMBER(5,2),
    notes CLOB,
    updated_by VARCHAR2(100),
    update_date DATE DEFAULT SYSDATE,
    created_date DATE DEFAULT SYSDATE,
    CONSTRAINT fk_pu_key_result FOREIGN KEY (key_result_id) REFERENCES key_results(key_result_id),
    CONSTRAINT fk_pu_objective FOREIGN KEY (objective_id) REFERENCES objectives(objective_id)
);

-- Create sequences for auto-incrementing IDs
CREATE SEQUENCE seq_objectives START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_key_results START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_progress_updates START WITH 1 INCREMENT BY 1;

-- Create triggers for auto-incrementing IDs
CREATE OR REPLACE TRIGGER tr_objectives_id
    BEFORE INSERT ON objectives
    FOR EACH ROW
BEGIN
    IF :NEW.objective_id IS NULL THEN
        :NEW.objective_id := seq_objectives.NEXTVAL;
    END IF;
    :NEW.updated_date := SYSDATE;
END;
/

CREATE OR REPLACE TRIGGER tr_key_results_id
    BEFORE INSERT ON key_results
    FOR EACH ROW
BEGIN
    IF :NEW.key_result_id IS NULL THEN
        :NEW.key_result_id := seq_key_results.NEXTVAL;
    END IF;
    :NEW.updated_date := SYSDATE;
END;
/

CREATE OR REPLACE TRIGGER tr_progress_updates_id
    BEFORE INSERT ON progress_updates
    FOR EACH ROW
BEGIN
    IF :NEW.update_id IS NULL THEN
        :NEW.update_id := seq_progress_updates.NEXTVAL;
    END IF;
END;
/

-- Create triggers to update timestamps
CREATE OR REPLACE TRIGGER tr_objectives_update
    BEFORE UPDATE ON objectives
    FOR EACH ROW
BEGIN
    :NEW.updated_date := SYSDATE;
END;
/

CREATE OR REPLACE TRIGGER tr_key_results_update
    BEFORE UPDATE ON key_results
    FOR EACH ROW
BEGIN
    :NEW.updated_date := SYSDATE;
END;
/

-- Insert sample data for testing
INSERT INTO objectives (title, description, owner_id, department, quarter, year, status, priority, target_completion_date)
VALUES ('Improve Customer Satisfaction', 'Increase customer satisfaction score to 95%', 'john.doe', 'Customer Success', 4, 2024, 'active', 'high', DATE '2024-12-31');

INSERT INTO objectives (title, description, owner_id, department, quarter, year, status, priority, target_completion_date)
VALUES ('Reduce Operational Costs', 'Cut operational costs by 15% through process optimization', 'jane.smith', 'Operations', 4, 2024, 'active', 'medium', DATE '2024-12-31');

INSERT INTO objectives (title, description, owner_id, department, quarter, year, status, priority, target_completion_date)
VALUES ('Launch New Product Line', 'Successfully launch 3 new products in Q4', 'bob.wilson', 'Product', 4, 2024, 'active', 'critical', DATE '2024-12-15');

-- Insert key results for the objectives
INSERT INTO key_results (objective_id, title, description, metric_type, target_value, current_value, unit, due_date)
VALUES (1, 'Customer Satisfaction Score', 'Achieve 95% customer satisfaction', 'percentage', 95, 87, 'percent', DATE '2024-12-31');

INSERT INTO key_results (objective_id, title, description, metric_type, target_value, current_value, unit, due_date)
VALUES (1, 'Response Time', 'Reduce average response time to under 2 hours', 'number', 2, 3.5, 'hours', DATE '2024-12-31');

INSERT INTO key_results (objective_id, title, description, metric_type, target_value, current_value, unit, due_date)
VALUES (2, 'Cost Reduction', 'Achieve 15% cost reduction', 'percentage', 15, 8, 'percent', DATE '2024-12-31');

INSERT INTO key_results (objective_id, title, description, metric_type, target_value, current_value, unit, due_date)
VALUES (2, 'Process Automation', 'Automate 10 manual processes', 'number', 10, 6, 'processes', DATE '2024-12-31');

INSERT INTO key_results (objective_id, title, description, metric_type, target_value, current_value, unit, due_date)
VALUES (3, 'Product Launches', 'Launch 3 new products', 'number', 3, 1, 'products', DATE '2024-12-15');

INSERT INTO key_results (objective_id, title, description, metric_type, target_value, current_value, unit, due_date)
VALUES (3, 'Market Penetration', 'Achieve 5% market share for new products', 'percentage', 5, 1.2, 'percent', DATE '2024-12-31');

-- Insert some progress updates
INSERT INTO progress_updates (key_result_id, objective_id, update_value, progress_percentage, notes, updated_by, update_date)
VALUES (1, 1, 87, 87, 'Customer satisfaction improved through better support training', 'john.doe', SYSDATE - 1);

INSERT INTO progress_updates (key_result_id, objective_id, update_value, progress_percentage, notes, updated_by, update_date)
VALUES (2, 1, 3.5, 65, 'Implemented new ticketing system, seeing gradual improvement', 'john.doe', SYSDATE - 1);

INSERT INTO progress_updates (key_result_id, objective_id, update_value, progress_percentage, notes, updated_by, update_date)
VALUES (3, 2, 8, 53, 'Cost reduction initiatives showing positive results', 'jane.smith', SYSDATE - 2);

INSERT INTO progress_updates (key_result_id, objective_id, update_value, progress_percentage, notes, updated_by, update_date)
VALUES (4, 2, 6, 60, 'Automated 6 processes, working on 4 more', 'jane.smith', SYSDATE - 1);

INSERT INTO progress_updates (key_result_id, objective_id, update_value, progress_percentage, notes, updated_by, update_date)
VALUES (5, 3, 1, 33, 'First product launched successfully, two more in development', 'bob.wilson', SYSDATE - 3);

-- Create indexes for better performance
CREATE INDEX idx_objectives_department ON objectives(department);
CREATE INDEX idx_objectives_status ON objectives(status);
CREATE INDEX idx_objectives_quarter_year ON objectives(quarter, year);
CREATE INDEX idx_key_results_objective ON key_results(objective_id);
CREATE INDEX idx_key_results_status ON key_results(status);
CREATE INDEX idx_progress_updates_kr ON progress_updates(key_result_id);
CREATE INDEX idx_progress_updates_date ON progress_updates(update_date);

COMMIT;

-- Show table creation results
SELECT 'Objectives table created with ' || COUNT(*) || ' sample records' as result FROM objectives;
SELECT 'Key Results table created with ' || COUNT(*) || ' sample records' as result FROM key_results;
SELECT 'Progress Updates table created with ' || COUNT(*) || ' sample records' as result FROM progress_updates;