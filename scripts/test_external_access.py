#!/usr/bin/env python3
"""
External Access Test Script for OKR Project
Tests connectivity to all services from outside Docker containers
"""

import requests
import json
import time
import logging
from typing import Dict, List, Tuple
import subprocess
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class ExternalAccessTester:
    def __init__(self, base_url: str = "http://localhost"):
        """Initialize the external access tester."""
        self.base_url = base_url
        self.results = {}

    def test_http_service(
        self,
        service_name: str,
        port: int,
        endpoint: str = "/",
        expected_status: int = 200,
    ) -> bool:
        """Test HTTP service accessibility."""
        try:
            url = f"{self.base_url}:{port}{endpoint}"
            logger.info(f"Testing {service_name} at {url}")

            response = requests.get(url, timeout=10)

            if response.status_code == expected_status:
                logger.info(
                    f"✓ {service_name} is accessible (Status: {response.status_code})"
                )
                self.results[service_name] = {
                    "status": "success",
                    "url": url,
                    "response_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                }
                return True
            else:
                logger.warning(
                    f"⚠ {service_name} responded with unexpected status: {response.status_code}"
                )
                self.results[service_name] = {
                    "status": "warning",
                    "url": url,
                    "response_code": response.status_code,
                    "error": f"Unexpected status code: {response.status_code}",
                }
                return False

        except requests.exceptions.ConnectionError:
            logger.error(f"✗ {service_name} connection failed - service not accessible")
            self.results[service_name] = {
                "status": "error",
                "url": f"{self.base_url}:{port}{endpoint}",
                "error": "Connection refused",
            }
            return False
        except requests.exceptions.Timeout:
            logger.error(f"✗ {service_name} request timed out")
            self.results[service_name] = {
                "status": "error",
                "url": f"{self.base_url}:{port}{endpoint}",
                "error": "Request timeout",
            }
            return False
        except Exception as e:
            logger.error(f"✗ {service_name} test failed: {e}")
            self.results[service_name] = {
                "status": "error",
                "url": f"{self.base_url}:{port}{endpoint}",
                "error": str(e),
            }
            return False

    def test_tcp_port(self, service_name: str, port: int) -> bool:
        """Test TCP port accessibility."""
        try:
            logger.info(f"Testing TCP port {port} for {service_name}")

            # Use netcat or telnet to test port
            result = subprocess.run(
                ["nc", "-z", "localhost", str(port)], capture_output=True, timeout=10
            )

            if result.returncode == 0:
                logger.info(f"✓ {service_name} port {port} is accessible")
                self.results[f"{service_name}_port_{port}"] = {
                    "status": "success",
                    "port": port,
                    "type": "tcp",
                }
                return True
            else:
                logger.error(f"✗ {service_name} port {port} is not accessible")
                self.results[f"{service_name}_port_{port}"] = {
                    "status": "error",
                    "port": port,
                    "type": "tcp",
                    "error": "Port not accessible",
                }
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"✗ {service_name} port {port} test timed out")
            self.results[f"{service_name}_port_{port}"] = {
                "status": "error",
                "port": port,
                "type": "tcp",
                "error": "Test timeout",
            }
            return False
        except FileNotFoundError:
            logger.warning(
                f"⚠ netcat not available, skipping TCP port test for {service_name}"
            )
            return True
        except Exception as e:
            logger.error(f"✗ {service_name} port {port} test failed: {e}")
            self.results[f"{service_name}_port_{port}"] = {
                "status": "error",
                "port": port,
                "type": "tcp",
                "error": str(e),
            }
            return False

    def test_kafka_connectivity(self) -> bool:
        """Test Kafka connectivity using kafka-console-consumer."""
        try:
            logger.info("Testing Kafka connectivity")

            # Test if we can connect to Kafka and list topics
            result = subprocess.run(
                ["kafka-topics.sh", "--list", "--bootstrap-server", "localhost:9092"],
                capture_output=True,
                timeout=15,
            )

            if result.returncode == 0:
                logger.info("✓ Kafka is accessible and responding")
                self.results["kafka"] = {
                    "status": "success",
                    "bootstrap_server": "localhost:9092",
                    "topics": (
                        result.stdout.decode().strip().split("\n")
                        if result.stdout
                        else []
                    ),
                }
                return True
            else:
                logger.error(f"✗ Kafka test failed: {result.stderr.decode()}")
                self.results["kafka"] = {
                    "status": "error",
                    "bootstrap_server": "localhost:9092",
                    "error": result.stderr.decode(),
                }
                return False

        except FileNotFoundError:
            logger.warning("⚠ kafka-topics.sh not available, skipping Kafka test")
            return True
        except subprocess.TimeoutExpired:
            logger.error("✗ Kafka test timed out")
            self.results["kafka"] = {
                "status": "error",
                "bootstrap_server": "localhost:9092",
                "error": "Test timeout",
            }
            return False
        except Exception as e:
            logger.error(f"✗ Kafka test failed: {e}")
            self.results["kafka"] = {
                "status": "error",
                "bootstrap_server": "localhost:9092",
                "error": str(e),
            }
            return False

    def test_airflow_api(self) -> bool:
        """Test Airflow API accessibility."""
        try:
            logger.info("Testing Airflow API")

            # Test Airflow health endpoint
            url = f"{self.base_url}:8081/health"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                logger.info(
                    f"✓ Airflow API is accessible (Status: {response.status_code})"
                )
                self.results["airflow_api"] = {
                    "status": "success",
                    "url": url,
                    "response_code": response.status_code,
                    "health_status": health_data.get("status", "unknown"),
                }
                return True
            else:
                logger.warning(
                    f"⚠ Airflow API responded with status: {response.status_code}"
                )
                self.results["airflow_api"] = {
                    "status": "warning",
                    "url": url,
                    "response_code": response.status_code,
                    "error": f"Unexpected status code: {response.status_code}",
                }
                return False

        except Exception as e:
            logger.error(f"✗ Airflow API test failed: {e}")
            self.results["airflow_api"] = {
                "status": "error",
                "url": f"{self.base_url}:8081/health",
                "error": str(e),
            }
            return False

    def run_all_tests(self) -> Dict[str, any]:
        """Run all external access tests."""
        logger.info("=== Starting External Access Tests ===")

        # Test HTTP services
        self.test_http_service("API Server", 5001, "/health")
        self.test_http_service("Nginx", 80, "/health")
        self.test_http_service("Airflow Web UI", 8081, "/")
        self.test_http_service("Kafka UI", 8085, "/")

        # Test TCP ports
        self.test_tcp_port("Kafka", 9092)
        self.test_tcp_port("Kafka External", 9094)
        self.test_tcp_port("Oracle Database", 1521)
        self.test_tcp_port("Oracle EM", 5500)

        # Test specialized services
        self.test_kafka_connectivity()
        self.test_airflow_api()

        logger.info("=== External Access Tests Completed ===")
        return self.results

    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        report = []
        report.append("# External Access Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        total_tests = len(self.results)
        successful_tests = sum(
            1 for r in self.results.values() if r["status"] == "success"
        )
        warning_tests = sum(
            1 for r in self.results.values() if r["status"] == "warning"
        )
        error_tests = sum(1 for r in self.results.values() if r["status"] == "error")

        report.append("## Summary")
        report.append(f"- Total Tests: {total_tests}")
        report.append(f"- Successful: {successful_tests}")
        report.append(f"- Warnings: {warning_tests}")
        report.append(f"- Errors: {error_tests}")
        report.append("")

        # Detailed Results
        report.append("## Detailed Results")
        for service_name, result in self.results.items():
            status_icon = {"success": "✓", "warning": "⚠", "error": "✗"}.get(
                result["status"], "?"
            )

            report.append(f"### {status_icon} {service_name}")

            if "url" in result:
                report.append(f"- URL: {result['url']}")

            if "port" in result:
                report.append(f"- Port: {result['port']}")

            if "response_code" in result:
                report.append(f"- Response Code: {result['response_code']}")

            if "error" in result:
                report.append(f"- Error: {result['error']}")

            if "health_status" in result:
                report.append(f"- Health Status: {result['health_status']}")

            report.append("")

        return "\n".join(report)

    def save_report(self, filename: str = "external_access_report.md"):
        """Save the test report to a file."""
        try:
            report = self.generate_report()
            with open(filename, "w") as f:
                f.write(report)
            logger.info(f"Report saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")


def main():
    """Main function to run external access tests."""
    # Check if base URL is provided as command line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost"

    logger.info(f"Testing external access with base URL: {base_url}")

    # Create tester and run tests
    tester = ExternalAccessTester(base_url)
    results = tester.run_all_tests()

    # Generate and save report
    tester.save_report()

    # Print summary
    successful = sum(1 for r in results.values() if r["status"] == "success")
    total = len(results)

    logger.info(f"Test Summary: {successful}/{total} tests passed")

    if successful == total:
        logger.info("🎉 All external access tests passed!")
        return 0
    else:
        logger.warning(
            "⚠ Some external access tests failed. Check the report for details."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
