#!/usr/bin/env python3
"""
Script to generate OpenAPI specification from running backend server
"""
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests module not found. Please install it with: pip install requests")
    sys.exit(1)

def main():
    # Configuration
    backend_url = "http://localhost:8000"
    openapi_endpoint = "/api/v1/openapi.json"
    frontend_dir = Path(__file__).parent / "frontend"
    output_file = frontend_dir / "openapi.json"
    
    # Fetch OpenAPI spec from backend
    try:
        print(f"Fetching OpenAPI spec from {backend_url}{openapi_endpoint}...")
        response = requests.get(f"{backend_url}{openapi_endpoint}", timeout=10)
        response.raise_for_status()
        
        openapi_spec = response.json()
        
        # Verify it's a valid OpenAPI spec
        if "openapi" not in openapi_spec and "swagger" not in openapi_spec:
            raise ValueError("Invalid OpenAPI specification received")
        
        # Write to frontend directory
        print(f"Writing OpenAPI spec to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
        
        print("✅ OpenAPI specification generated successfully!")
        print(f"Now run 'npm run generate-client' in the frontend directory to update client code.")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to backend server.")
        print("Please make sure the backend server is running on http://localhost:8000")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Error: Request timeout. Backend server may be slow to respond.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error: HTTP {e.response.status_code} - {e.response.reason}")
        if e.response.status_code == 404:
            print("The OpenAPI endpoint was not found. Check the backend configuration.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()