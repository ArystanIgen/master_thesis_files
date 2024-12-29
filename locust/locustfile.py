import json
import random
import logging
import string
from locust import HttpUser, SequentialTaskSet, task, between, LoadTestShape

logger = logging.getLogger(__name__)

# Load pre-generated TSP data
with open('generated_tsp_data.json', 'r') as f:
    TSP_DATA = json.load(f)

if not TSP_DATA:
    logger.warning("No TSP data found. Please ensure generated_tsp_data.json is populated.")


def random_id(prefix="test", length=5):
    """Generate a random alphanumeric suffix and prepend a given prefix."""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}-{suffix}"


def assert_response(response, success_codes=(200,), failure_message="Request failed"):
    """Assert that the response code is among success_codes, otherwise fail."""
    if response.status_code not in success_codes:
        response.failure(f"{failure_message}: Status {response.status_code}, Body: {response.text}")
        logger.error(f"{failure_message}: {response.text}")


class TSPScenario(SequentialTaskSet):
    """
    Scenario simulating CRUD operations on Transport Service Providers.
    Uses generated TSP data for more realistic payloads.
    """
    created_tsp_id = None

    @task
    def create_tsp(self):
        """Create a TSP based on random pre-generated data."""
        # Pick a random TSP entry from the loaded data as a template
        base_data = random.choice(TSP_DATA)
        payload = {
            "id": random_id("test-tsp"),
            "name": base_data.get("TSP Name", "LoadTest TSP " + random_id("test-tsp")),
            "countries": base_data.get("Countries", ["Germany"]),
            "tsp_type": base_data.get("TSP Type", "Airline"),
            "time_slots": base_data.get("Time Slots", ["Mornings"])
        }
        with self.client.post("/v1/discovery/tsps", json=payload, name="POST /tsps", catch_response=True) as response:
            if response.status_code == 200:
                self.created_tsp_id = response.json().get("id")
                logger.info(f"Created TSP with ID: {self.created_tsp_id}")
            else:
                assert_response(response, failure_message="Failed to create TSP")

    @task
    def get_tsps(self):
        """Retrieve a paginated list of TSPs."""
        with self.client.get("/v1/discovery/tsps?size=10", name="GET /tsps", catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response, failure_message="Failed to GET TSPs")

    @task
    def update_tsp(self):
        """Update the name of the created TSP."""
        if not self.created_tsp_id:
            logger.warning("No TSP ID available to update.")
            return
        payload = {"name": "Updated LoadTest TSP Name"}
        with self.client.patch(f"/v1/discovery/tsps/{self.created_tsp_id}",
                               json=payload,
                               name="PATCH /tsps/{id}",
                               catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response, failure_message=f"Failed to update TSP {self.created_tsp_id}")
            else:
                logger.info(f"Updated TSP {self.created_tsp_id}")

    @task
    def get_recommendations(self):
        """Fetch recommendations for the created TSP."""
        tsp_id = self.created_tsp_id or "dummy-tsp-id"
        params = {"countries": ["Germany"], "tsp_types": ["Airline"], "time_slots": ["Mornings"]}
        with self.client.get(f"/v1/discovery/tsps/{tsp_id}/recommendations",
                             params=params,
                             name="GET /tsps/{id}/recommendations",
                             catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response, failure_message=f"Failed to get recommendations for {tsp_id}")

    @task
    def delete_tsp(self):
        """Delete the created TSP."""
        if not self.created_tsp_id:
            logger.warning("No TSP ID available to delete.")
            return
        with self.client.delete(f"/v1/discovery/tsps/{self.created_tsp_id}",
                                name="DELETE /tsps/{id}",
                                catch_response=True) as response:
            if response.status_code not in (200, 204):
                assert_response(response, failure_message=f"Failed to delete TSP {self.created_tsp_id}")
            else:
                logger.info(f"Deleted TSP {self.created_tsp_id}")
                self.created_tsp_id = None


class GoalScenario(SequentialTaskSet):
    """
    Scenario simulating CRUD operations on Goals.
    """
    goal_id = None

    @task
    def create_goal(self):
        """Create a new Goal."""
        payload = {
            "name": "Test Goal " + random_id(),
            "tsp_provider": "Airline",
            "tsp_consumer": "Bus operators",
            "data_requirements": ["AL1.1", "AL1.2"]
        }
        with self.client.post("/v1/discovery/goals", json=payload, name="POST /goals", catch_response=True) as response:
            if response.status_code == 200:
                self.goal_id = response.json().get("id")
                logger.info(f"Created Goal with ID: {self.goal_id}")
            else:
                assert_response(response, failure_message="Failed to create goal")

    @task
    def get_goals(self):
        """Retrieve a list of Goals."""
        with self.client.get("/v1/discovery/goals", name="GET /goals", catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response, failure_message="Failed to get goals")

    @task
    def update_goal(self):
        """Update the name of an existing Goal."""
        if not self.goal_id:
            logger.warning("No Goal ID available to update.")
            return
        payload = {"name": "Updated Test Goal"}
        with self.client.patch(f"/v1/discovery/goals/{self.goal_id}", json=payload,
                               name="PATCH /goals/{id}", catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response, failure_message=f"Failed to update goal {self.goal_id}")
            else:
                logger.info(f"Updated Goal {self.goal_id}")

    @task
    def get_goal_data_requirements(self):
        """Fetch data requirements for the existing Goal."""
        if not self.goal_id:
            logger.warning("No Goal ID available to fetch data requirements.")
            return
        with self.client.get(f"/v1/discovery/goals/{self.goal_id}/data-requirements",
                             name="GET /goals/{id}/data-requirements", catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response, failure_message=f"Failed to get data requirements for goal {self.goal_id}")
            else:
                logger.info(f"Fetched data requirements for Goal {self.goal_id}")


class DataRequirementScenario(SequentialTaskSet):
    """
    Scenario simulating operations on Data Requirements.
    """
    data_req_code = "AL1.1"

    @task
    def get_data_requirement_by_code(self):
        """Retrieve the Data Requirement by code."""
        with self.client.get(f"/v1/discovery/data-requirements/{self.data_req_code}",
                             name="GET /data-requirements/{code}",
                             catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response,
                                failure_message=f"Failed to retrieve data requirement by code {self.data_req_code}")
            else:
                logger.info(f"Retrieved Data Requirement with code: {self.data_req_code}")

    @task
    def validate_data_requirements(self):
        """Validate a list of Data Requirements."""
        payload = ["AL2.2", "INVALID456"]
        with self.client.post("/v1/discovery/data-requirements/validate", json=payload,
                              name="POST /data-requirements/validate", catch_response=True) as response:
            if response.status_code != 200:
                assert_response(response, failure_message="Failed to validate data requirements")
            else:
                logger.info(f"Validated Data Requirements: {payload}")


class DiscoveryServiceUser(HttpUser):
    """
    A simulated user interacting with the Discovery Service.
    Executes scenarios sequentially.
    """
    tasks = [TSPScenario, GoalScenario, DataRequirementScenario]
    wait_time = between(1, 2)  # Simulate realistic user delays

# locust --users 30 --spawn-rate 3 -f locust/locustfile.py --host=http://localhost:9000
