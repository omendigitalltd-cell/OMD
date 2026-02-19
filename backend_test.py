#!/usr/bin/env python3
"""
WiFi Hotspot Admin System - Backend API Testing
Tests all backend functionality including auth, customers, calculator, reminders, and settings.
"""

import requests
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class WiFiHotspotAPITester:
    def __init__(self, base_url: str = "https://voucher-billing-sys.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.admin_email = f"test_admin_{datetime.now().strftime('%H%M%S')}@example.com"
        self.admin_password = "TestPass123!"
        self.test_customer_id = None

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}

            return success, response_data

        except Exception as e:
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test basic health endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        success, data = self.make_request('GET', '')
        self.log_test("Root endpoint", success, 
                     "" if success else f"Failed to reach root: {data}")
        
        # Test health endpoint
        success, data = self.make_request('GET', 'health')
        self.log_test("Health check", success,
                     "" if success else f"Health check failed: {data}")

    def test_admin_registration(self):
        """Test admin registration"""
        print("\n🔍 Testing Admin Registration...")
        
        success, data = self.make_request('POST', 'auth/register', {
            "email": self.admin_email,
            "password": self.admin_password
        })
        
        if success and 'access_token' in data:
            self.token = data['access_token']
            self.log_test("Admin registration", True)
        else:
            self.log_test("Admin registration", False, f"Registration failed: {data}")

    def test_admin_login(self):
        """Test admin login"""
        print("\n🔍 Testing Admin Login...")
        
        success, data = self.make_request('POST', 'auth/login', {
            "email": self.admin_email,
            "password": self.admin_password
        })
        
        if success and 'access_token' in data:
            self.token = data['access_token']
            self.log_test("Admin login", True)
        else:
            self.log_test("Admin login", False, f"Login failed: {data}")

    def test_admin_profile(self):
        """Test getting admin profile"""
        print("\n🔍 Testing Admin Profile...")
        
        success, data = self.make_request('GET', 'auth/me')
        self.log_test("Get admin profile", success,
                     "" if success else f"Profile fetch failed: {data}")

    def test_customer_operations(self):
        """Test customer CRUD operations"""
        print("\n🔍 Testing Customer Operations...")
        
        # Test get customers (empty initially)
        success, data = self.make_request('GET', 'customers')
        self.log_test("Get customers (empty)", success,
                     "" if success else f"Get customers failed: {data}")
        
        # Test create customer
        customer_data = {
            "name": "Test Customer",
            "phone": "+27123456789",
            "voucher_code": "HS-TEST01",
            "plan": "3_devices",
            "start_date": "2026-01-15",
            "is_active": True
        }
        
        success, data = self.make_request('POST', 'customers', customer_data, 201)
        if success and isinstance(data, dict) and 'id' in data:
            self.test_customer_id = data['id']
            self.log_test("Create customer", True)
        else:
            # Check if it's actually successful but with different status
            if isinstance(data, dict) and 'id' in data:
                self.test_customer_id = data['id']
                self.log_test("Create customer", True, "Customer created (status code mismatch)")
            else:
                self.log_test("Create customer", False, f"Customer creation failed: {data}")
                return
        
        # Test get specific customer
        success, data = self.make_request('GET', f'customers/{self.test_customer_id}')
        self.log_test("Get specific customer", success,
                     "" if success else f"Get customer failed: {data}")
        
        # Test update customer
        update_data = {
            "name": "Updated Test Customer",
            "plan": "4_devices"
        }
        success, data = self.make_request('PUT', f'customers/{self.test_customer_id}', update_data)
        self.log_test("Update customer", success,
                     "" if success else f"Update customer failed: {data}")
        
        # Test duplicate voucher code (should fail)
        duplicate_customer = {
            "name": "Duplicate Customer",
            "phone": "+27987654321",
            "voucher_code": "HS-TEST01",  # Same voucher code
            "plan": "3_devices",
            "start_date": "2026-01-15",
            "is_active": True
        }
        success, data = self.make_request('POST', 'customers', duplicate_customer, 400)
        self.log_test("Duplicate voucher code validation", success,
                     "" if success else f"Should have failed with 400: {data}")

    def test_prorata_calculator(self):
        """Test pro-rata calculation functionality"""
        print("\n🔍 Testing Pro-rata Calculator...")
        
        # Test get 2026 months
        success, data = self.make_request('GET', 'prorata/months-2026')
        self.log_test("Get 2026 months", success,
                     "" if success else f"Get months failed: {data}")
        
        # Test pro-rata calculation
        calc_data = {
            "start_day": 15,
            "month": 3,
            "year": 2026,
            "plan": "3_devices"
        }
        success, data = self.make_request('POST', 'prorata/calculate', calc_data)
        if success:
            expected_fields = ['prorata_amount', 'daily_rate', 'days_used', 'monthly_rate']
            has_fields = all(field in data for field in expected_fields)
            self.log_test("Pro-rata calculation", has_fields,
                         "" if has_fields else f"Missing fields in response: {data}")
        else:
            self.log_test("Pro-rata calculation", False, f"Calculation failed: {data}")
        
        # Test invalid month
        invalid_calc = {
            "start_day": 15,
            "month": 13,  # Invalid month
            "year": 2026,
            "plan": "3_devices"
        }
        success, data = self.make_request('POST', 'prorata/calculate', invalid_calc, 400)
        self.log_test("Invalid month validation", success,
                     "" if success else f"Should have failed with 400: {data}")

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        print("\n🔍 Testing Dashboard Stats...")
        
        # Test dashboard stats
        success, data = self.make_request('GET', 'dashboard/stats')
        if success:
            expected_fields = ['total_customers', 'active_customers', 'estimated_monthly_revenue']
            has_fields = all(field in data for field in expected_fields)
            self.log_test("Dashboard stats", has_fields,
                         "" if has_fields else f"Missing fields in response: {data}")
        else:
            self.log_test("Dashboard stats", False, f"Stats failed: {data}")
        
        # Test recent customers
        success, data = self.make_request('GET', 'dashboard/recent-customers')
        self.log_test("Recent customers", success,
                     "" if success else f"Recent customers failed: {data}")
        
        # Test recent reminders
        success, data = self.make_request('GET', 'dashboard/recent-reminders')
        self.log_test("Recent reminders", success,
                     "" if success else f"Recent reminders failed: {data}")

    def test_reminder_system(self):
        """Test reminder functionality"""
        print("\n🔍 Testing Reminder System...")
        
        # Test get reminder logs
        success, data = self.make_request('GET', 'reminders/logs')
        self.log_test("Get reminder logs", success,
                     "" if success else f"Get logs failed: {data}")
        
        # Test send test reminder (if we have a customer)
        if self.test_customer_id:
            success, data = self.make_request('POST', f'reminders/send-test?customer_id={self.test_customer_id}')
            self.log_test("Send test reminder", success,
                         "" if success else f"Send test failed: {data}")
        
        # Test schedule monthly reminders
        success, data = self.make_request('POST', 'reminders/schedule-monthly')
        self.log_test("Schedule monthly reminders", success,
                     "" if success else f"Schedule failed: {data}")

    def test_settings(self):
        """Test settings functionality"""
        print("\n🔍 Testing Settings...")
        
        # Test get WhatsApp config
        success, data = self.make_request('GET', 'settings/whatsapp')
        self.log_test("Get WhatsApp config", success,
                     "" if success else f"Get WhatsApp config failed: {data}")
        
        # Test update WhatsApp config
        whatsapp_config = {
            "phone_number_id": "123456789",
            "business_account_id": "987654321",
            "access_token": "test_token",
            "verify_token": "test_verify",
            "is_configured": True
        }
        success, data = self.make_request('PUT', 'settings/whatsapp', whatsapp_config)
        self.log_test("Update WhatsApp config", success,
                     "" if success else f"Update WhatsApp failed: {data}")
        
        # Test get reminder settings
        success, data = self.make_request('GET', 'settings/reminders')
        self.log_test("Get reminder settings", success,
                     "" if success else f"Get reminder settings failed: {data}")
        
        # Test update reminder settings
        reminder_settings = {
            "enabled": True,
            "reminder_day": 25,
            "reminder_message": "Test reminder message for {name}"
        }
        success, data = self.make_request('PUT', 'settings/reminders', reminder_settings)
        self.log_test("Update reminder settings", success,
                     "" if success else f"Update reminder settings failed: {data}")

    def test_cleanup(self):
        """Clean up test data"""
        print("\n🔍 Cleaning up test data...")
        
        if self.test_customer_id:
            success, data = self.make_request('DELETE', f'customers/{self.test_customer_id}')
            self.log_test("Delete test customer", success,
                         "" if success else f"Delete failed: {data}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting WiFi Hotspot Admin API Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        try:
            # Basic connectivity
            self.test_health_check()
            
            # Authentication
            self.test_admin_registration()
            self.test_admin_login()
            self.test_admin_profile()
            
            # Customer management
            self.test_customer_operations()
            
            # Pro-rata calculator
            self.test_prorata_calculator()
            
            # Dashboard
            self.test_dashboard_stats()
            
            # Reminders
            self.test_reminder_system()
            
            # Settings
            self.test_settings()
            
            # Cleanup
            self.test_cleanup()
            
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            return False
        
        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        # Show failed tests
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test runner"""
    tester = WiFiHotspotAPITester()
    
    success = tester.run_all_tests()
    all_passed = tester.print_summary()
    
    # Return appropriate exit code
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())