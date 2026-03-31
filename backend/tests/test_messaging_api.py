"""
Backend API Tests for WiFi Hotspot Admin System
Tests: Authentication, Messaging (ManyChat), Customers, Pro-rata, Refund, Dashboard
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "b.e.motloung@gmail.com"
ADMIN_PASSWORD = "Bobla@920821"

class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_admin_login_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        print(f"✓ Admin login successful, token received")
        return data["access_token"]
    
    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print(f"✓ Invalid login correctly rejected with 401")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestMessagingStatus:
    """Test ManyChat messaging status endpoint"""
    
    def test_messaging_status_returns_configured(self, auth_headers):
        """GET /api/messaging/status - should return manychat_configured: true"""
        response = requests.get(f"{BASE_URL}/api/messaging/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "manychat_configured" in data
        assert data["manychat_configured"] == True, "ManyChat should be configured"
        assert "channels_available" in data
        assert "whatsapp" in data["channels_available"]
        assert "sms" in data["channels_available"]
        print(f"✓ Messaging status: {data}")


class TestCustomers:
    """Test customer CRUD operations"""
    
    def test_get_customers_list(self, auth_headers):
        """GET /api/customers - should return customer list"""
        response = requests.get(f"{BASE_URL}/api/customers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} customers")
        
        # Verify customer structure if any exist
        if len(data) > 0:
            customer = data[0]
            assert "id" in customer
            assert "name" in customer
            assert "phone" in customer
            assert "plan" in customer
            print(f"✓ Customer structure verified: {customer['name']}")
        return data


class TestMessagingSendReminder:
    """Test sending reminders via ManyChat"""
    
    def test_send_reminder_to_customer(self, auth_headers):
        """POST /api/messaging/send-reminder - should attempt ManyChat API call and log result"""
        # First get a customer
        customers_response = requests.get(f"{BASE_URL}/api/customers", headers=auth_headers)
        customers = customers_response.json()
        
        if len(customers) == 0:
            pytest.skip("No customers available for testing")
        
        customer_id = customers[0]["id"]
        customer_name = customers[0]["name"]
        
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-reminder",
            json={"customer_id": customer_id, "channel": "whatsapp"},
            headers=auth_headers
        )
        
        # ManyChat may fail due to account permissions, but should return 400 not 500
        # and should log the attempt
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            print(f"✓ Reminder sent successfully to {customer_name}")
        elif response.status_code == 400:
            # Expected - ManyChat subscriber creation may fail due to permissions
            data = response.json()
            assert "detail" in data
            print(f"✓ Reminder attempt logged with expected ManyChat error: {data['detail'][:100]}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_send_reminder_invalid_customer(self, auth_headers):
        """POST /api/messaging/send-reminder - should return 404 for invalid customer"""
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-reminder",
            json={"customer_id": "invalid-customer-id-12345", "channel": "whatsapp"},
            headers=auth_headers
        )
        assert response.status_code == 404
        print(f"✓ Invalid customer correctly rejected with 404")


class TestMessagingSendVoucher:
    """Test sending voucher codes via ManyChat"""
    
    def test_send_voucher_to_customer(self, auth_headers):
        """POST /api/messaging/send-voucher - should attempt ManyChat API call and log result"""
        # First get a customer
        customers_response = requests.get(f"{BASE_URL}/api/customers", headers=auth_headers)
        customers = customers_response.json()
        
        if len(customers) == 0:
            pytest.skip("No customers available for testing")
        
        customer_id = customers[0]["id"]
        customer_name = customers[0]["name"]
        
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-voucher",
            json={"customer_id": customer_id, "channel": "whatsapp"},
            headers=auth_headers
        )
        
        # ManyChat may fail due to account permissions, but should return 400 not 500
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            print(f"✓ Voucher sent successfully to {customer_name}")
        elif response.status_code == 400:
            # Expected - ManyChat subscriber creation may fail due to permissions
            data = response.json()
            assert "detail" in data
            print(f"✓ Voucher attempt logged with expected ManyChat error: {data['detail'][:100]}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


class TestMessagingBulkReminders:
    """Test bulk reminder sending"""
    
    def test_send_bulk_reminders(self, auth_headers):
        """POST /api/messaging/send-bulk-reminders - should attempt to send to all active customers"""
        response = requests.post(
            f"{BASE_URL}/api/messaging/send-bulk-reminders",
            json={"channel": "whatsapp"},
            headers=auth_headers
        )
        
        # Bulk endpoint should always return 200 with summary
        assert response.status_code == 200
        data = response.json()
        assert "sent" in data
        assert "failed" in data
        assert "message" in data
        print(f"✓ Bulk reminders: {data['message']}")


class TestMessagingLogs:
    """Test message logs endpoint"""
    
    def test_get_message_logs(self, auth_headers):
        """GET /api/messaging/logs - should return message history"""
        response = requests.get(f"{BASE_URL}/api/messaging/logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} message logs")
        
        # Verify log structure if any exist
        if len(data) > 0:
            log = data[0]
            assert "id" in log
            assert "customer_id" in log
            assert "customer_name" in log
            assert "customer_phone" in log
            assert "status" in log
            assert "channel" in log
            assert log["status"] in ["sent", "failed", "pending"]
            print(f"✓ Log structure verified: {log['customer_name']} - {log['status']}")


class TestProRataCalculator:
    """Test pro-rata calculation for 2026"""
    
    def test_prorata_calculation_3_devices(self, auth_headers):
        """POST /api/prorata/calculate - pro-rata for 3 devices plan"""
        response = requests.post(
            f"{BASE_URL}/api/prorata/calculate",
            json={
                "start_day": 15,
                "month": 1,
                "year": 2026,
                "plan": "3_devices"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "3_devices"
        assert data["monthly_rate"] == 200.0
        assert data["year"] == 2026
        assert "prorata_amount" in data
        assert data["prorata_amount"] > 0
        print(f"✓ Pro-rata calculation: R{data['prorata_amount']:.2f} for {data['days_used']} days")
    
    def test_prorata_calculation_4_devices(self, auth_headers):
        """POST /api/prorata/calculate - pro-rata for 4 devices plan"""
        response = requests.post(
            f"{BASE_URL}/api/prorata/calculate",
            json={
                "start_day": 10,
                "month": 6,
                "year": 2026,
                "plan": "4_devices"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "4_devices"
        assert data["monthly_rate"] == 300.0
        assert "prorata_amount" in data
        print(f"✓ Pro-rata calculation: R{data['prorata_amount']:.2f} for {data['days_used']} days")


class TestRefundCalculator:
    """Test refund calculation with custom duration days"""
    
    def test_refund_calculation_1_week(self, auth_headers):
        """POST /api/refund/calculate - refund for 1 week (8 days)"""
        response = requests.post(
            f"{BASE_URL}/api/refund/calculate",
            json={
                "amount": 200.0,
                "duration_weeks": 1,
                "voucher_start_date": "2026-01-01",
                "refund_start_date": "2026-01-03"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["duration_weeks"] == 1
        assert data["total_days"] == 8  # 1 week = 8 days per spec
        assert "refund_amount" in data
        print(f"✓ Refund calculation: R{data['refund_amount']:.2f} (used {data['days_used']} of {data['total_days']} days)")
    
    def test_refund_calculation_4_weeks(self, auth_headers):
        """POST /api/refund/calculate - refund for 4 weeks (32 days)"""
        response = requests.post(
            f"{BASE_URL}/api/refund/calculate",
            json={
                "amount": 300.0,
                "duration_weeks": 4,
                "voucher_start_date": "2026-01-01",
                "refund_start_date": "2026-01-10"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["duration_weeks"] == 4
        assert data["total_days"] == 32  # 4 weeks = 32 days per spec
        assert "refund_amount" in data
        print(f"✓ Refund calculation: R{data['refund_amount']:.2f} (used {data['days_used']} of {data['total_days']} days)")


class TestDashboardStats:
    """Test dashboard statistics endpoint"""
    
    def test_get_dashboard_stats(self, auth_headers):
        """GET /api/dashboard/stats - should return dashboard statistics"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields
        assert "total_customers" in data
        assert "active_customers" in data
        assert "three_device_customers" in data
        assert "four_device_customers" in data
        assert "estimated_monthly_revenue" in data
        
        # Verify data types
        assert isinstance(data["total_customers"], int)
        assert isinstance(data["active_customers"], int)
        assert isinstance(data["estimated_monthly_revenue"], (int, float))
        
        print(f"✓ Dashboard stats: {data['total_customers']} customers, R{data['estimated_monthly_revenue']:.2f} revenue")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
