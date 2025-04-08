from typing import Tuple

class LocalPrefectServer:
    
    def change_prefect_settings():
        
        
    def start_local_server():
        pass

    @staticmethod
    def test_prefect_api(api_url:str) -> Tuple[bool,str]:
        """Test connection to Prefect server"""
        try:
            import requests
            from requests.exceptions import ConnectionError, Timeout
            
            # Simple connection test with timeout
            response = requests.get(
                api_url, 
                timeout=3,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                return False, f"Error: response_code: {response.status_code}, reason: {response.reason} - {response.content}"
            
            return True, ""
            
            # return response.status_code < 500  # Consider any non-5xx response as success
        except (ConnectionError, Timeout):
            return False,""
        except Exception as e:
            print(f"Error testing Prefect connection: {str(e)}")
            return False,""