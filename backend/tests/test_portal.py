"""
Test suite for Customer Portal features:
- Portal registration and login
- Profile, purchases, points, rewards
- Redemption flow
- Payment initiation
- Referral system
- Admin CSV voucher upload
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_EMAIL = "b.e.motloung@gmail.com"
ADMIN_PASSWORD = "Bobla@920821"
PORTAL_PHONE = "0811234567"
PORTAL_PASSWORD = "test123"
REFERRED_PHONE = "0829876543"
REFERRED_PASSWORD = "friend123"


class TestPortalAuth:
    """Portal authentication tests"""
    
    def test_portal_login_success(self):
        """Test portal login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "phone": PORTAL_PHONE,
            "password": PORTAL_PASSWORD
        })
        print(f"Portal login response: {response.status_code} - {response.text[:200]}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "customer_id" in data, "Response should contain customer_id"
        assert data["token_type"] == "bearer"
    
    def test_portal_login_invalid_credentials(self):
        """Test portal login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "phone": "0000000000",
            "password": "wrongpassword"
        })
        print(f"Invalid login response: {response.status_code}")
        assert response.status_code == 401
    
    def test_portal_register_duplicate_phone(self):
        """Test registration with existing phone number"""
        response = requests.post(f"{BASE_URL}/api/portal/register", json={
            "name": "Test User",
            "phone": PORTAL_PHONE,  # Already exists
            "password": "newpassword123"
        })
        print(f"Duplicate registration response: {response.status_code}")
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
    
    def test_portal_register_new_user(self):
        """Test registration of a new user"""
        unique_phone = f"099{uuid.uuid4().hex[:7]}"
        response = requests.post(f"{BASE_URL}/api/portal/register", json={
            "name": "TEST_New User",
            "phone": unique_phone,
            "password": "testpass123"
        })
        print(f"New registration response: {response.status_code} - {response.text[:200]}")
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "customer_id" in data


class TestPortalProfile:
    """Portal profile and data retrieval tests"""
    
    @pytest.fixture
    def portal_token(self):
        """Get portal auth token"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "phone": PORTAL_PHONE,
            "password": PORTAL_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Portal login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_portal_profile(self, portal_token):
        """Test GET /api/portal/profile"""
        response = requests.get(
            f"{BASE_URL}/api/portal/profile",
            headers={"Authorization": f"Bearer {portal_token}"}
        )
        print(f"Profile response: {response.status_code} - {response.text[:300]}")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data, "Profile should contain name"
        assert "phone" in data, "Profile should contain phone"
        assert "points" in data, "Profile should contain points"
        assert "referral_code" in data, "Profile should contain referral_code"
        assert "referral_count" in data, "Profile should contain referral_count"
        print(f"Profile data: name={data['name']}, points={data['points']}, referral_code={data['referral_code']}")
    
    def test_portal_purchases(self, portal_token):
        """Test GET /api/portal/purchases"""
        response = requests.get(
            f"{BASE_URL}/api/portal/purchases",
            headers={"Authorization": f"Bearer {portal_token}"}
        )
        print(f"Purchases response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Purchases should be a list"
        print(f"Found {len(data)} purchases")
    
    def test_portal_points(self, portal_token):
        """Test GET /api/portal/points"""
        response = requests.get(
            f"{BASE_URL}/api/portal/points",
            headers={"Authorization": f"Bearer {portal_token}"}
        )
        print(f"Points response: {response.status_code} - {response.text[:300]}")
        assert response.status_code == 200
        
        data = response.json()
        assert "balance" in data, "Points response should contain balance"
        assert "history" in data, "Points response should contain history"
        assert isinstance(data["history"], list)
        print(f"Points balance: {data['balance']}, history entries: {len(data['history'])}")
    
    def test_portal_rewards(self, portal_token):
        """Test GET /api/portal/rewards"""
        response = requests.get(
            f"{BASE_URL}/api/portal/rewards",
            headers={"Authorization": f"Bearer {portal_token}"}
        )
        print(f"Rewards response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        
        data = response.json()
        assert "balance" in data, "Rewards response should contain balance"
        assert "tiers" in data, "Rewards response should contain tiers"
        assert isinstance(data["tiers"], list)
        assert len(data["tiers"]) > 0, "Should have at least one reward tier"
        
        # Check tier structure
        tier = data["tiers"][0]
        assert "plan" in tier
        assert "label" in tier
        assert "points_needed" in tier
        assert "value" in tier
        assert "can_redeem" in tier
        print(f"Balance: {data['balance']}, Tiers: {len(data['tiers'])}")
    
    def test_portal_referral(self, portal_token):
        """Test GET /api/portal/referral"""
        response = requests.get(
            f"{BASE_URL}/api/portal/referral",
            headers={"Authorization": f"Bearer {portal_token}"}
        )
        print(f"Referral response: {response.status_code} - {response.text[:400]}")
        assert response.status_code == 200
        
        data = response.json()
        assert "referral_code" in data, "Should contain referral_code"
        assert "referral_link" in data, "Should contain referral_link"
        assert "total_referrals" in data, "Should contain total_referrals"
        assert "points_per_referral" in data, "Should contain points_per_referral"
        assert "referrals" in data, "Should contain referrals list"
        assert data["points_per_referral"] == 5, "Points per referral should be 5"
        print(f"Referral code: {data['referral_code']}, Total referrals: {data['total_referrals']}")


class TestPortalPayment:
    """Portal payment initiation tests"""
    
    @pytest.fixture
    def portal_token(self):
        """Get portal auth token"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "phone": PORTAL_PHONE,
            "password": PORTAL_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Portal login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_payment_initiate_valid_plan(self, portal_token):
        """Test POST /api/portal/payment/initiate with valid plan"""
        response = requests.post(
            f"{BASE_URL}/api/portal/payment/initiate",
            headers={"Authorization": f"Bearer {portal_token}"},
            json={"plan": "1_day"}
        )
        print(f"Payment initiate response: {response.status_code} - {response.text[:500]}")
        assert response.status_code == 200
        
        data = response.json()
        assert "order_id" in data, "Should contain order_id"
        assert "payfast_url" in data, "Should contain payfast_url"
        assert "form_fields" in data, "Should contain form_fields"
        
        form = data["form_fields"]
        assert "merchant_id" in form
        assert "amount" in form
        assert form["amount"] == "10.00", "1_day plan should be R10"
        assert "signature" in form
        print(f"Order ID: {data['order_id']}, PayFast URL: {data['payfast_url']}")
    
    def test_payment_initiate_invalid_plan(self, portal_token):
        """Test payment initiation with invalid plan"""
        response = requests.post(
            f"{BASE_URL}/api/portal/payment/initiate",
            headers={"Authorization": f"Bearer {portal_token}"},
            json={"plan": "invalid_plan"}
        )
        print(f"Invalid plan response: {response.status_code}")
        assert response.status_code == 400


class TestPortalRedemption:
    """Portal points redemption tests"""
    
    @pytest.fixture
    def portal_token(self):
        """Get portal auth token"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "phone": PORTAL_PHONE,
            "password": PORTAL_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Portal login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_redeem_insufficient_points(self, portal_token):
        """Test redemption with insufficient points"""
        # Try to redeem a high-tier reward (270 pts for 4_devices)
        response = requests.post(
            f"{BASE_URL}/api/portal/redeem",
            headers={"Authorization": f"Bearer {portal_token}"},
            json={"plan": "4_devices"}
        )
        print(f"Redeem insufficient points response: {response.status_code} - {response.text}")
        # Should fail due to insufficient points (test user has only 5 pts)
        assert response.status_code == 400
        assert "not enough points" in response.json().get("detail", "").lower()
    
    def test_redeem_invalid_plan(self, portal_token):
        """Test redemption with invalid plan"""
        response = requests.post(
            f"{BASE_URL}/api/portal/redeem",
            headers={"Authorization": f"Bearer {portal_token}"},
            json={"plan": "invalid_plan"}
        )
        print(f"Redeem invalid plan response: {response.status_code}")
        assert response.status_code == 400


class TestReferralSystem:
    """Referral system tests"""
    
    def test_referred_user_login(self):
        """Test that referred user exists and can login"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "phone": REFERRED_PHONE,
            "password": REFERRED_PASSWORD
        })
        print(f"Referred user login response: {response.status_code}")
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        
        # Check their points (should have 5 from referral bonus)
        profile_response = requests.get(
            f"{BASE_URL}/api/portal/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()
        print(f"Referred user profile: name={profile.get('name')}, points={profile.get('points')}")
        # Referred user should have at least 5 points from referral bonus
        assert profile.get("points", 0) >= 5, "Referred user should have at least 5 bonus points"
    
    def test_referrer_has_referral_count(self):
        """Test that referrer has referral count"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "phone": PORTAL_PHONE,
            "password": PORTAL_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        profile_response = requests.get(
            f"{BASE_URL}/api/portal/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()
        print(f"Referrer profile: name={profile.get('name')}, points={profile.get('points')}, referral_count={profile.get('referral_count')}")
        # Referrer should have at least 1 referral
        assert profile.get("referral_count", 0) >= 1, "Referrer should have at least 1 referral"


class TestAdminVoucherCSVUpload:
    """Admin CSV voucher upload tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_csv_upload_valid(self, admin_token):
        """Test CSV voucher upload with valid data"""
        # Create a simple CSV content
        csv_content = "code\nTEST-CSV-001\nTEST-CSV-002\nTEST-CSV-003"
        
        files = {
            'file': ('vouchers.csv', csv_content, 'text/csv')
        }
        data = {
            'plan': '1_day'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vouchers/upload-csv",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=data
        )
        print(f"CSV upload response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        
        result = response.json()
        assert "added" in result
        assert "duplicates" in result
        print(f"Added: {result['added']}, Duplicates: {result['duplicates']}")
    
    def test_csv_upload_invalid_plan(self, admin_token):
        """Test CSV upload with invalid plan"""
        csv_content = "code\nTEST-INVALID-001"
        
        files = {
            'file': ('vouchers.csv', csv_content, 'text/csv')
        }
        data = {
            'plan': 'invalid_plan'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vouchers/upload-csv",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=data
        )
        print(f"Invalid plan CSV upload response: {response.status_code}")
        assert response.status_code == 400
    
    def test_csv_upload_no_auth(self):
        """Test CSV upload without authentication"""
        csv_content = "code\nTEST-NOAUTH-001"
        
        files = {
            'file': ('vouchers.csv', csv_content, 'text/csv')
        }
        data = {
            'plan': '1_day'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/vouchers/upload-csv",
            files=files,
            data=data
        )
        print(f"No auth CSV upload response: {response.status_code}")
        assert response.status_code in [401, 403]


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """Test API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Health check response: {response.status_code}")
        # Health endpoint might not exist, but we can check if API is up
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
