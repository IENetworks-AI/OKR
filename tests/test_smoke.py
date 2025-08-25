import os


def test_repo_has_core_files():
    assert os.path.exists('docker-compose.yml')
    assert os.path.exists('apps/api/app.py')
    assert os.path.exists('src/dags/etl_pipeline.py')

