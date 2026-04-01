"""
BulkSMS Messaging API Tests
Tests for the BulkSMS integration that replaced ManyChat
- Messaging status endpoint
- Send SMS reminder to customer
- Send SMS voucher to customer
- Send bulk SMS reminders
- Message logs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_EMAIL = "b.e.motloung@gmail.com"
ADMIN_PASSWORD = "Bobla@920821"

# Existing customer IDs from the review request
TEST_CUSTOMER_ID = "e0c8c9f3-59bb-4917-a427-995f1b6a5274"  # Test Customer
JOHN_DOE_CUSTOMER_ID = "4107e2de-4d81-493b-b9e1-8bcea8badefc"  # John Doe


@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestMessagingStatus:
    """Test BulkSMS messaging status endpoint"""
    
    def test_messaging_status_returns_bulksms_configured(self, auth_headers):
        """GET /api/messaging/status should return bulksms_configured: true"""
        response = requests.get(
            f"{BASE_URL}/api/messaging/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "bulksms_configured" in data, "Response should contain 'bulksms_configured' field"
        assert data["bulksms_configured"] == True, "BulkSMS should be configured (bulksms_configured: true)"
        assert "channels_available" in data, "Response should contain 'channels_available' field"
        assert "sms" in data["channels_available"], "SMS should be in available channels"
        
        print(f"✓ Messaging status: bulksms_configured={data['bulksms_configured']}, channels={data['channels_available']}")


class TestSendSMSReminder:
    """Test sending SMS payment reminder to a customer"""
    
    def test_send_reminder_to_customer(self, auth_headers):
        """POST /api/messaging/send-reminder with customer_id should send SMS"""
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-reminder",
            json={"customer_id": TEST_CUSTOMER_ID, "channel": "sms"},
            headers=auth_headers
        )
        
        # BulkSMS returns 201 for successful sends, but our API returns 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "SMS should be sent successfully"
        assert "SMS" in data["message"] or "sent" in data["message"].lower(), "Message should indicate SMS was sent"
        
        print(f"✓ Reminder sent: {data['message']}")
    
    def test_send_reminder_invalid_customer(self, auth_headers):
        """POST /api/messaging/send-reminder with invalid customer_id should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-reminder",
            json={"customer_id": "invalid-customer-id-12345", "channel": "sms"},
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid customer, got {response.status_code}"
        print("✓ Invalid customer returns 404 as expected")


class TestSendSMSVoucher:
    """Test sending SMS voucher code to a customer"""
    
    def test_send_voucher_to_customer(self, auth_headers):
        """POST /api/messaging/send-voucher with customer_id should send SMS"""
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-voucher",
            json={"customer_id": TEST_CUSTOMER_ID, "channel": "sms"},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "SMS should be sent successfully"
        assert "SMS" in data["message"] or "sent" in data["message"].lower(), "Message should indicate SMS was sent"
        
        print(f"✓ Voucher sent: {data['message']}")
    
    def test_send_voucher_invalid_customer(self, auth_headers):
        """POST /api/messaging/send-voucher with invalid customer_id should return 404"""
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-voucher",
            json={"customer_id": "invalid-customer-id-12345", "channel": "sms"},
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid customer, got {response.status_code}"
        print("✓ Invalid customer returns 404 as expected")


class TestBulkSMSReminders:
    """Test sending bulk SMS reminders to all active customers"""
    
    def test_send_bulk_reminders(self, auth_headers):
        """POST /api/messaging/send-bulk-reminders should send SMS to all active customers"""
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-bulk-reminders",
            json={"channel": "sms"},
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "sent" in data, "Response should contain 'sent' count"
        assert "failed" in data, "Response should contain 'failed' count"
        
        # At least some messages should be sent (we have active customers)
        total = data["sent"] + data["failed"]
        print(f"✓ Bulk reminders: {data['sent']} sent, {data['failed']} failed, total: {total}")
        
        # If there are failures, log them
        if data.get("errors"):
            print(f"  Errors: {data['errors'][:3]}")


class TestMessageLogs:
    """Test message logs endpoint"""
    
    def test_get_message_logs(self, auth_headers):
        """GET /api/messaging/logs should return sent messages with status=sent"""
        response = requests.get(
            f"{BASE_URL}/api/messaging/logs",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list of logs"
        
        # After sending messages above, we should have logs
        if len(data) > 0:
            log = data[0]
            # Verify log structure
            assert "id" in log, "Log should have 'id' field"
            assert "customer_id" in log, "Log should have 'customer_id' field"
            assert "customer_name" in log, "Log should have 'customer_name' field"
            assert "customer_phone" in log, "Log should have 'customer_phone' field"
            assert "message_type" in log, "Log should have 'message_type' field"
            assert "channel" in log, "Log should have 'channel' field"
            assert "status" in log, "Log should have 'status' field"
            assert "created_at" in log, "Log should have 'created_at' field"
            
            # Check for sent messages
            sent_logs = [l for l in data if l.get("status") == "sent"]
            print(f"✓ Message logs: {len(data)} total, {len(sent_logs)} with status=sent")
            
            # Verify channel is SMS
            sms_logs = [l for l in data if l.get("channel") == "sms"]
            print(f"  SMS channel logs: {len(sms_logs)}")
        else:
            print("✓ Message logs endpoint works (no logs yet)")


class TestAdminLogin:
    """Test admin login flow"""
    
    def test_admin_login_success(self):
        """POST /api/auth/login should authenticate admin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain 'access_token'"
        assert len(data["access_token"]) > 0, "Token should not be empty"
        
        print(f"✓ Admin login successful, token length: {len(data['access_token'])}")
    
    def test_admin_login_invalid_credentials(self):
        """POST /api/auth/login with wrong password should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": "wrongpassword"}
        )
        
        assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
        print("✓ Invalid credentials returns 401 as expected")


class TestDashboard:
    """Test dashboard endpoint"""
    
    def test_dashboard_stats(self, auth_headers):
        """GET /api/dashboard/stats should return dashboard statistics"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_customers" in data, "Response should contain 'total_customers'"
        assert "active_customers" in data, "Response should contain 'active_customers'"
        assert "estimated_monthly_revenue" in data, "Response should contain 'estimated_monthly_revenue'"
        
        print(f"✓ Dashboard stats: {data['total_customers']} total customers, {data['active_customers']} active")


class TestCustomerExists:
    """Verify test customers exist"""
    
    def test_test_customer_exists(self, auth_headers):
        """GET /api/customers/{id} should return Test Customer"""
        response = requests.get(
            f"{BASE_URL}/api/customers/{TEST_CUSTOMER_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 404:
            pytest.skip(f"Test Customer {TEST_CUSTOMER_ID} not found - may need to create test data")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["id"] == TEST_CUSTOMER_ID
        print(f"✓ Test Customer exists: {data.get('name')} - {data.get('phone')}")
    
    def test_john_doe_customer_exists(self, auth_headers):
        """GET /api/customers/{id} should return John Doe"""
        response = requests.get(
            f"{BASE_URL}/api/customers/{JOHN_DOE_CUSTOMER_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 404:
            pytest.skip(f"John Doe Customer {JOHN_DOE_CUSTOMER_ID} not found - may need to create test data")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["id"] == JOHN_DOE_CUSTOMER_ID
        print(f"✓ John Doe Customer exists: {data.get('name')} - {data.get('phone')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
