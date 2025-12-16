"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Soccer Team": {
            "description": "Join the school soccer team and compete in regional tournaments",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 6:00 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "chris@mergington.edu"]
        },
        "Swimming Club": {
            "description": "Improve your swimming technique and participate in swim meets",
            "schedule": "Mondays and Wednesdays, 3:00 PM - 4:30 PM",
            "max_participants": 15,
            "participants": ["sarah@mergington.edu"]
        },
        "Drama Club": {
            "description": "Perform in school plays and develop acting skills",
            "schedule": "Wednesdays, 3:30 PM - 5:30 PM",
            "max_participants": 20,
            "participants": ["lily@mergington.edu", "james@mergington.edu"]
        },
    })
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Soccer Team" in data
        assert "Swimming Club" in data
        assert "Drama Club" in data
    
    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post("/activities/Soccer%20Team/signup?email=newstudent@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post("/activities/Nonexistent%20Activity/signup?email=student@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_student(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "alex@mergington.edu"
        response = client.post(f"/activities/Soccer%20Team/signup?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_multiple_students(self, client):
        """Test signing up multiple students for an activity"""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for student in students:
            response = client.post(f"/activities/Swimming%20Club/signup?email={student}")
            assert response.status_code == 200
        
        # Verify all students were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for student in students:
            assert student in activities_data["Swimming Club"]["participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "alex@mergington.edu"
        response = client.delete(f"/activities/Soccer%20Team/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistration from an activity that doesn't exist"""
        response = client.delete("/activities/Nonexistent%20Activity/unregister?email=student@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_non_registered_student(self, client):
        """Test that unregistering a non-registered student fails"""
        email = "nonregistered@mergington.edu"
        response = client.delete(f"/activities/Soccer%20Team/unregister?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is not registered for this activity"
    
    def test_unregister_and_resigup(self, client):
        """Test that a student can unregister and sign up again"""
        email = "sarah@mergington.edu"
        activity = "Swimming Club"
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Sign up again
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify the participant is registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]


class TestActivityWorkflow:
    """Integration tests for complete workflows"""
    
    def test_full_signup_workflow(self, client):
        """Test complete workflow: get activities, signup, verify"""
        # Get initial activities
        response = client.get("/activities")
        assert response.status_code == 200
        initial_data = response.json()
        initial_count = len(initial_data["Drama Club"]["participants"])
        
        # Sign up new student
        email = "newdrama@mergington.edu"
        response = client.post(f"/activities/Drama%20Club/signup?email={email}")
        assert response.status_code == 200
        
        # Verify updated activities
        response = client.get("/activities")
        updated_data = response.json()
        assert len(updated_data["Drama Club"]["participants"]) == initial_count + 1
        assert email in updated_data["Drama Club"]["participants"]
    
    def test_full_unregister_workflow(self, client):
        """Test complete workflow: get activities, unregister, verify"""
        # Get initial activities
        response = client.get("/activities")
        assert response.status_code == 200
        initial_data = response.json()
        initial_count = len(initial_data["Soccer Team"]["participants"])
        
        # Unregister student
        email = "alex@mergington.edu"
        response = client.delete(f"/activities/Soccer%20Team/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify updated activities
        response = client.get("/activities")
        updated_data = response.json()
        assert len(updated_data["Soccer Team"]["participants"]) == initial_count - 1
        assert email not in updated_data["Soccer Team"]["participants"]
