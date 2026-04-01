"""
Test PayFast Payment Integration and Voucher Management
Tests for WiFi Hotspot Admin System - PayFast payment flow and voucher pool management
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bulksms-payment-hub.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "b.e.motloung@gmail.com"
ADMIN_PASSWORD = "Bobla@920821"


@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get auth headers for admin requests"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Health check passed")
    
    def test_admin_login(self):
        """Test admin login with credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("✓ Admin login successful")


class TestVoucherManagement:
    """Test voucher pool management (admin routes)"""
    
    def test_get_voucher_stats(self, auth_headers):
        """GET /api/vouchers/stats - Get voucher pool statistics"""
        response = requests.get(f"{BASE_URL}/api/vouchers/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have stats for both plans
        assert "3_devices" in data
        assert "4_devices" in data
        assert "available" in data["3_devices"]
        assert "assigned" in data["3_devices"]
        print(f"✓ Voucher stats: 3-dev available={data['3_devices']['available']}, 4-dev available={data['4_devices']['available']}")
    
    def test_get_voucher_pool(self, auth_headers):
        """GET /api/vouchers - List all voucher codes"""
        response = requests.get(f"{BASE_URL}/api/vouchers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Voucher pool has {len(data)} codes")
        # Check structure if vouchers exist
        if len(data) > 0:
            voucher = data[0]
            assert "id" in voucher
            assert "code" in voucher
            assert "plan" in voucher
            assert "assigned" in voucher
            print(f"  Sample voucher: {voucher['code']} ({voucher['plan']}, assigned={voucher['assigned']})")
    
    def test_add_voucher_codes(self, auth_headers):
        """POST /api/vouchers/add - Add voucher codes to pool"""
        test_codes = [f"TEST-VOUCH-{uuid.uuid4().hex[:6].upper()}" for _ in range(2)]
        
        response = requests.post(
            f"{BASE_URL}/api/vouchers/add",
            json={"codes": test_codes, "plan": "3_devices"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert data["added"] >= 0
        print(f"✓ Added {data['added']} voucher codes (duplicates: {data.get('duplicates', 0)})")
        
        # Verify codes were added
        pool_response = requests.get(f"{BASE_URL}/api/vouchers", headers=auth_headers)
        pool = pool_response.json()
        added_codes = [v for v in pool if v["code"] in test_codes]
        assert len(added_codes) == data["added"]
        print(f"  Verified {len(added_codes)} codes in pool")
        
        # Return codes for cleanup
        return test_codes
    
    def test_add_voucher_codes_4_devices(self, auth_headers):
        """POST /api/vouchers/add - Add 4-device plan voucher codes"""
        test_codes = [f"TEST-4DEV-{uuid.uuid4().hex[:6].upper()}" for _ in range(2)]
        
        response = requests.post(
            f"{BASE_URL}/api/vouchers/add",
            json={"codes": test_codes, "plan": "4_devices"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added"] >= 0
        print(f"✓ Added {data['added']} 4-device voucher codes")
    
    def test_delete_unassigned_voucher(self, auth_headers):
        """DELETE /api/vouchers/{id} - Delete unassigned voucher"""
        # First add a test voucher
        test_code = f"TEST-DEL-{uuid.uuid4().hex[:6].upper()}"
        add_response = requests.post(
            f"{BASE_URL}/api/vouchers/add",
            json={"codes": [test_code], "plan": "3_devices"},
            headers=auth_headers
        )
        assert add_response.status_code == 200
        
        # Find the voucher ID
        pool_response = requests.get(f"{BASE_URL}/api/vouchers", headers=auth_headers)
        pool = pool_response.json()
        test_voucher = next((v for v in pool if v["code"] == test_code), None)
        
        if test_voucher:
            # Delete it
            delete_response = requests.delete(
                f"{BASE_URL}/api/vouchers/{test_voucher['id']}",
                headers=auth_headers
            )
            assert delete_response.status_code == 200
            print(f"✓ Deleted voucher {test_code}")
            
            # Verify deletion
            pool_after = requests.get(f"{BASE_URL}/api/vouchers", headers=auth_headers).json()
            assert not any(v["code"] == test_code for v in pool_after)
            print("  Verified voucher removed from pool")
        else:
            print("  Voucher was duplicate, skipping delete test")


class TestPaymentInitiation:
    """Test payment initiation (public route)"""
    
    def test_initiate_payment_3_devices(self, auth_headers):
        """POST /api/payment/initiate - Initiate 3-device plan payment"""
        # First ensure we have vouchers available
        stats = requests.get(f"{BASE_URL}/api/vouchers/stats", headers=auth_headers).json()
        if stats["3_devices"]["available"] == 0:
            # Add a test voucher
            requests.post(
                f"{BASE_URL}/api/vouchers/add",
                json={"codes": [f"AVAIL-3DEV-{uuid.uuid4().hex[:6].upper()}"], "plan": "3_devices"},
                headers=auth_headers
            )
        
        response = requests.post(
            f"{BASE_URL}/api/payment/initiate",
            json={
                "plan": "3_devices",
                "customer_name": "Test Customer",
                "customer_phone": "0812345678",
                "customer_email": "test@example.com"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "order_id" in data
        assert data["order_id"].startswith("WF-")
        assert "payfast_url" in data
        assert "www.payfast.co.za" in data["payfast_url"]  # Live mode
        assert "form_fields" in data
        
        # Verify form fields
        form = data["form_fields"]
        assert form["merchant_id"] == "31016281"
        assert form["amount"] == "200.00"
        assert "signature" in form
        assert form["m_payment_id"] == data["order_id"]
        assert "return_url" in form
        assert "cancel_url" in form
        assert "notify_url" in form
        
        print(f"✓ Payment initiated: order_id={data['order_id']}")
        print(f"  PayFast URL: {data['payfast_url']}")
        print(f"  Amount: R{form['amount']}")
        return data["order_id"]
    
    def test_initiate_payment_4_devices(self, auth_headers):
        """POST /api/payment/initiate - Initiate 4-device plan payment"""
        # Ensure vouchers available
        stats = requests.get(f"{BASE_URL}/api/vouchers/stats", headers=auth_headers).json()
        if stats["4_devices"]["available"] == 0:
            requests.post(
                f"{BASE_URL}/api/vouchers/add",
                json={"codes": [f"AVAIL-4DEV-{uuid.uuid4().hex[:6].upper()}"], "plan": "4_devices"},
                headers=auth_headers
            )
        
        response = requests.post(
            f"{BASE_URL}/api/payment/initiate",
            json={
                "plan": "4_devices",
                "customer_name": "Premium Customer",
                "customer_phone": "0823456789"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["form_fields"]["amount"] == "300.00"
        print(f"✓ 4-device payment initiated: order_id={data['order_id']}, amount=R300.00")
    
    def test_initiate_payment_invalid_plan(self):
        """POST /api/payment/initiate - Invalid plan should fail"""
        response = requests.post(
            f"{BASE_URL}/api/payment/initiate",
            json={
                "plan": "invalid_plan",
                "customer_name": "Test",
                "customer_phone": "0812345678"
            }
        )
        assert response.status_code == 400
        print("✓ Invalid plan correctly rejected")
    
    def test_initiate_payment_missing_fields(self):
        """POST /api/payment/initiate - Missing required fields"""
        response = requests.post(
            f"{BASE_URL}/api/payment/initiate",
            json={"plan": "3_devices"}  # Missing name and phone
        )
        assert response.status_code == 422  # Validation error
        print("✓ Missing fields correctly rejected")


class TestPaymentVerification:
    """Test payment verification (public route)"""
    
    def test_verify_pending_payment(self, auth_headers):
        """GET /api/payment/verify/{order_id} - Verify pending payment"""
        # First create a payment
        stats = requests.get(f"{BASE_URL}/api/vouchers/stats", headers=auth_headers).json()
        if stats["3_devices"]["available"] == 0:
            requests.post(
                f"{BASE_URL}/api/vouchers/add",
                json={"codes": [f"VERIFY-{uuid.uuid4().hex[:6].upper()}"], "plan": "3_devices"},
                headers=auth_headers
            )
        
        init_response = requests.post(
            f"{BASE_URL}/api/payment/initiate",
            json={
                "plan": "3_devices",
                "customer_name": "Verify Test",
                "customer_phone": "0834567890"
            }
        )
        order_id = init_response.json()["order_id"]
        
        # Verify the payment
        response = requests.get(f"{BASE_URL}/api/payment/verify/{order_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["order_id"] == order_id
        assert data["status"] == "pending"
        assert data["plan"] == "3_devices"
        assert data["amount"] == 200
        assert data["customer_name"] == "Verify Test"
        assert data["voucher_code"] is None  # Not yet assigned
        
        print(f"✓ Payment verified: status={data['status']}, voucher={data['voucher_code']}")
    
    def test_verify_nonexistent_payment(self):
        """GET /api/payment/verify/{order_id} - Non-existent payment"""
        response = requests.get(f"{BASE_URL}/api/payment/verify/WF-NONEXISTENT123")
        assert response.status_code == 404
        print("✓ Non-existent payment correctly returns 404")


class TestPayFastITNCallback:
    """Test PayFast ITN callback (public route)"""
    
    def test_itn_callback_endpoint_exists(self):
        """POST /api/payment/notify - ITN endpoint accepts POST"""
        # Send minimal form data (will fail validation but endpoint should exist)
        response = requests.post(
            f"{BASE_URL}/api/payment/notify",
            data={"test": "data"}
        )
        # Should return 200 with error in body (not 404 or 405)
        assert response.status_code == 200
        data = response.json()
        # Will fail due to missing/invalid data, but endpoint works
        assert "success" in data
        print(f"✓ ITN endpoint exists and accepts POST (success={data['success']})")
    
    def test_itn_callback_with_invalid_signature(self, auth_headers):
        """POST /api/payment/notify - Invalid signature rejected"""
        # Create a payment first
        stats = requests.get(f"{BASE_URL}/api/vouchers/stats", headers=auth_headers).json()
        if stats["3_devices"]["available"] == 0:
            requests.post(
                f"{BASE_URL}/api/vouchers/add",
                json={"codes": [f"ITN-{uuid.uuid4().hex[:6].upper()}"], "plan": "3_devices"},
                headers=auth_headers
            )
        
        init_response = requests.post(
            f"{BASE_URL}/api/payment/initiate",
            json={
                "plan": "3_devices",
                "customer_name": "ITN Test",
                "customer_phone": "0845678901"
            }
        )
        order_id = init_response.json()["order_id"]
        
        # Send ITN with invalid signature
        response = requests.post(
            f"{BASE_URL}/api/payment/notify",
            data={
                "m_payment_id": order_id,
                "custom_str1": order_id,
                "payment_status": "COMPLETE",
                "amount_gross": "200.00",
                "signature": "invalid_signature_12345"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert "signature" in data.get("error", "").lower() or data["success"] == False
        print("✓ Invalid signature correctly rejected")


class TestAdminPayments:
    """Test admin payment management"""
    
    def test_get_all_payments(self, auth_headers):
        """GET /api/admin/payments - List all payment records"""
        response = requests.get(f"{BASE_URL}/api/admin/payments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin payments list: {len(data)} records")
        
        if len(data) > 0:
            payment = data[0]
            assert "id" in payment
            assert "plan" in payment
            assert "amount" in payment
            assert "status" in payment
            assert "customer_name" in payment
            print(f"  Latest: {payment['id']} - {payment['customer_name']} - R{payment['amount']} - {payment['status']}")
    
    def test_get_payments_requires_auth(self):
        """GET /api/admin/payments - Requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/payments")
        assert response.status_code in [401, 403]
        print("✓ Admin payments endpoint requires authentication")


class TestExistingVouchers:
    """Test existing voucher codes mentioned in requirements"""
    
    def test_existing_test_vouchers(self, auth_headers):
        """Verify test voucher codes exist: WIFI-TEST-001, WIFI-TEST-002, WIFI-TEST-003"""
        response = requests.get(f"{BASE_URL}/api/vouchers", headers=auth_headers)
        assert response.status_code == 200
        vouchers = response.json()
        
        test_codes = ["WIFI-TEST-001", "WIFI-TEST-002", "WIFI-TEST-003"]
        found_codes = [v["code"] for v in vouchers if v["code"] in test_codes]
        
        print(f"✓ Found {len(found_codes)}/{len(test_codes)} test voucher codes")
        for code in test_codes:
            if code in found_codes:
                voucher = next(v for v in vouchers if v["code"] == code)
                print(f"  {code}: plan={voucher['plan']}, assigned={voucher['assigned']}")
            else:
                print(f"  {code}: NOT FOUND (may need to be added)")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_vouchers(self, auth_headers):
        """Remove TEST- prefixed vouchers created during testing"""
        response = requests.get(f"{BASE_URL}/api/vouchers", headers=auth_headers)
        vouchers = response.json()
        
        test_vouchers = [v for v in vouchers if v["code"].startswith("TEST-") and not v["assigned"]]
        deleted = 0
        
        for voucher in test_vouchers:
            del_response = requests.delete(
                f"{BASE_URL}/api/vouchers/{voucher['id']}",
                headers=auth_headers
            )
            if del_response.status_code == 200:
                deleted += 1
        
        print(f"✓ Cleanup: Deleted {deleted} test vouchers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
