#!/usr/bin/env python
"""
DDoS Protection Testing Suite
Tests all three middleware protection layers
Run this from your project root directory: python test_ddos.py
"""

import requests
import threading
import time
from colorama import init, Fore, Style
import sys

# Initialize colorama for colored output
init(autoreset=True)

# Configuration
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/login/"
REGISTER_URL = f"{BASE_URL}/register/"
HOME_URL = f"{BASE_URL}/"

# Test results storage
results = {
    'rate_limit': {'passed': 0, 'blocked': 0},
    'auth_limit': {'passed': 0, 'blocked': 0},
    'connection_limit': {'passed': 0, 'blocked': 0},
    'payload_limit': {'passed': 0, 'blocked': 0}
}

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"{Fore.CYAN}{Style.BRIGHT}  {text}")
    print("="*70)

def print_success(text):
    """Print success message"""
    print(f"{Fore.GREEN}✓ {text}")

def print_error(text):
    """Print error message"""
    print(f"{Fore.RED}✗ {text}")

def print_info(text):
    """Print info message"""
    print(f"{Fore.YELLOW}ℹ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"{Fore.MAGENTA}⚠ {text}")

def test_server_availability():
    """Check if the server is running"""
    print_header("Testing Server Availability")
    try:
        response = requests.get(HOME_URL, timeout=5)
        if response.status_code in [200, 302]:
            print_success(f"Server is running at {BASE_URL}")
            return True
        else:
            print_error(f"Server responded with status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to server: {e}")
        print_info("Make sure your Django server is running: python manage.py runserver")
        return False

def test_rate_limit():
    """Test general rate limiting (100 requests per 60 seconds)"""
    print_header("TEST 1: Rate Limit Protection")
    print_info("Sending 150 requests to test rate limiting...")
    print_info("Expected: First ~100 should pass, rest should be blocked")
    
    for i in range(150):
        try:
            response = requests.get(HOME_URL, timeout=2)
            
            if response.status_code == 200 or response.status_code == 302:
                results['rate_limit']['passed'] += 1
                if i < 5 or i > 95:  # Show first 5 and around blocking point
                    print(f"  Request {i+1:3d}: {Fore.GREEN}✓ Success (200/302)")
            elif response.status_code == 403 or response.status_code == 429:
                results['rate_limit']['blocked'] += 1
                if results['rate_limit']['blocked'] <= 5:  # Show first 5 blocks
                    print(f"  Request {i+1:3d}: {Fore.RED}✗ BLOCKED ({response.status_code})")
            else:
                print(f"  Request {i+1:3d}: {Fore.YELLOW}? Unexpected ({response.status_code})")
                
        except requests.exceptions.RequestException as e:
            results['rate_limit']['blocked'] += 1
            if results['rate_limit']['blocked'] <= 3:
                print(f"  Request {i+1:3d}: {Fore.RED}✗ Connection error")
        
        time.sleep(0.05)  # Small delay to not overwhelm the server instantly
    
    # Summary
    print(f"\n{Fore.CYAN}Results:")
    print(f"  ✓ Passed: {results['rate_limit']['passed']}")
    print(f"  ✗ Blocked: {results['rate_limit']['blocked']}")
    
    if results['rate_limit']['blocked'] > 30:
        print_success("Rate limiting is WORKING! ✓")
    else:
        print_warning("Rate limiting might not be working properly")

def test_auth_rate_limit():
    """Test authentication rate limiting (5 attempts per 60 seconds)"""
    print_header("TEST 2: Authentication Rate Limit")
    print_info("Sending 10 login attempts to test auth rate limiting...")
    print_info("Expected: First 5 should process, rest should be blocked")
    
    # Get CSRF token first
    session = requests.Session()
    try:
        response = session.get(LOGIN_URL)
        csrf_token = session.cookies.get('csrftoken', '')
    except:
        csrf_token = ''
    
    for i in range(10):
        try:
            response = session.post(LOGIN_URL, 
                data={
                    'username': f'test_user_{i}',
                    'password': f'wrong_password_{i}',
                    'csrfmiddlewaretoken': csrf_token
                },
                timeout=2,
                allow_redirects=False
            )
            
            if response.status_code in [200, 302, 403]:
                if response.status_code == 403:
                    results['auth_limit']['blocked'] += 1
                    print(f"  Attempt {i+1:2d}: {Fore.RED}✗ BLOCKED (403)")
                else:
                    results['auth_limit']['passed'] += 1
                    print(f"  Attempt {i+1:2d}: {Fore.GREEN}✓ Processed ({response.status_code})")
            elif response.status_code == 429:
                results['auth_limit']['blocked'] += 1
                print(f"  Attempt {i+1:2d}: {Fore.RED}✗ BLOCKED (429 - Too Many Requests)")
            else:
                print(f"  Attempt {i+1:2d}: {Fore.YELLOW}? Unexpected ({response.status_code})")
                
        except requests.exceptions.RequestException:
            results['auth_limit']['blocked'] += 1
            print(f"  Attempt {i+1:2d}: {Fore.RED}✗ Connection blocked")
        
        time.sleep(0.2)
    
    # Summary
    print(f"\n{Fore.CYAN}Results:")
    print(f"  ✓ Processed: {results['auth_limit']['passed']}")
    print(f"  ✗ Blocked: {results['auth_limit']['blocked']}")
    
    if results['auth_limit']['blocked'] >= 3:
        print_success("Auth rate limiting is WORKING! ✓")
    else:
        print_warning("Auth rate limiting might not be working properly")

def test_concurrent_connections():
    """Test concurrent connection limiting (10 connections per IP)"""
    print_header("TEST 3: Concurrent Connection Limit")
    print_info("Opening 20 concurrent connections...")
    print_info("Expected: First 10 should succeed, rest should be blocked")
    
    def make_request(thread_id, results_list):
        try:
            response = requests.get(HOME_URL, timeout=5)
            results_list.append({
                'thread': thread_id,
                'status': response.status_code,
                'success': True
            })
        except Exception as e:
            results_list.append({
                'thread': thread_id,
                'error': str(e),
                'success': False
            })
    
    threads = []
    thread_results = []
    
    # Start 20 threads simultaneously
    for i in range(20):
        thread = threading.Thread(target=make_request, args=(i+1, thread_results))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Analyze results
    successful = sum(1 for r in thread_results if r.get('success'))
    failed = sum(1 for r in thread_results if not r.get('success'))
    
    print(f"\n{Fore.CYAN}Results:")
    print(f"  ✓ Successful connections: {successful}")
    print(f"  ✗ Failed/Blocked connections: {failed}")
    
    results['connection_limit']['passed'] = successful
    results['connection_limit']['blocked'] = failed
    
    if failed >= 5:
        print_success("Connection throttling is WORKING! ✓")
    else:
        print_warning("Connection throttling might not be working as expected")

def test_large_payload():
    """Test large payload protection (10 MB limit)"""
    print_header("TEST 4: Large Payload Protection")
    print_info("Attempting to send a 15 MB payload...")
    print_info("Expected: Request should be blocked")
    
    # Create a large payload (15 MB)
    large_data = "A" * (15 * 1024 * 1024)  # 15 MB of data
    
    try:
        response = requests.post(
            REGISTER_URL,
            data={'large_field': large_data},
            timeout=10
        )
        
        if response.status_code == 403:
            results['payload_limit']['blocked'] += 1
            print_success("Large payload was BLOCKED! ✓")
        else:
            results['payload_limit']['passed'] += 1
            print_warning(f"Large payload was processed (Status: {response.status_code})")
            
    except requests.exceptions.RequestException as e:
        results['payload_limit']['blocked'] += 1
        print_success(f"Large payload was BLOCKED! (Connection error)")

def print_final_summary():
    """Print final test summary"""
    print_header("FINAL SUMMARY")
    
    total_tests = 4
    passed_tests = 0
    
    # Rate Limit Test
    if results['rate_limit']['blocked'] > 30:
        print_success("✓ Rate Limiting: WORKING")
        passed_tests += 1
    else:
        print_error("✗ Rate Limiting: NOT WORKING")
    
    # Auth Rate Limit Test
    if results['auth_limit']['blocked'] >= 3:
        print_success("✓ Auth Rate Limiting: WORKING")
        passed_tests += 1
    else:
        print_error("✗ Auth Rate Limiting: NOT WORKING")
    
    # Connection Throttling Test
    if results['connection_limit']['blocked'] >= 5:
        print_success("✓ Connection Throttling: WORKING")
        passed_tests += 1
    else:
        print_error("✗ Connection Throttling: NOT WORKING")
    
    # Payload Limit Test
    if results['payload_limit']['blocked'] > 0:
        print_success("✓ Payload Size Limiting: WORKING")
        passed_tests += 1
    else:
        print_warning("⚠ Payload Size Limiting: UNTESTED/NOT WORKING")
    
    # Overall result
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}Overall Score: {passed_tests}/{total_tests} tests passed")
    print(f"{Fore.CYAN}{'='*70}\n")
    
    if passed_tests == total_tests:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 ALL PROTECTION MECHANISMS ARE WORKING! 🎉")
    elif passed_tests >= total_tests - 1:
        print(f"{Fore.YELLOW}{Style.BRIGHT}⚠ Most protections working, but some issues detected")
    else:
        print(f"{Fore.RED}{Style.BRIGHT}❌ DDoS protection needs attention!")

def main():
    """Main test runner"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                  DDoS PROTECTION TEST SUITE                        ║")
    print("║                                                                    ║")
    print("║  This will test all three middleware protection layers            ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(Style.RESET_ALL)
    
    # Check if server is running
    if not test_server_availability():
        sys.exit(1)
    
    print_info("\nStarting tests in 3 seconds...")
    time.sleep(3)
    
    try:
        # Run all tests
        test_rate_limit()
        time.sleep(2)
        
        test_auth_rate_limit()
        time.sleep(2)
        
        test_concurrent_connections()
        time.sleep(2)
        
        test_large_payload()
        
        # Print summary
        print_final_summary()
        
    except KeyboardInterrupt:
        print_warning("\n\nTests interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()