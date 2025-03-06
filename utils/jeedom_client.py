import json
import os
import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv

class JeedomClient:
    def __init__(self):
        # Force reload environment variables
        load_dotenv(override=True)
        self.url = os.getenv("JEEDOM_URL")
        self.api_key = os.getenv("JEEDOM_KEY")
        
        print(f"Initializing JeedomClient with URL: {self.url}")  # Debug print
        print(f"API Key: {self.api_key[:5]}...")  # Debug print first 5 chars of API key
        
        if not self.url or not self.api_key:
            raise ValueError("JEEDOM_URL and JEEDOM_KEY must be set in .env file")
            
        # Remove trailing slash from URL if present
        self.url = self.url.rstrip('/')
        
    def get_full_data(self):
        """Get full data from Jeedom API"""
        try:
            url = f"{self.url}/core/api/jeeApi.php"
            params = {
                "apikey": self.api_key,
                "type": "fullData"
            }
            
            print(f"Making request to Jeedom API: {url}")  # Debug print
            response = requests.get(url, params=params)
            print(f"Response status code: {response.status_code}")  # Debug print
            
            if response.status_code == 200:
                data = response.json()
                print(f"Received data: {json.dumps(data, indent=2)}")  # Debug print
                return data
            else:
                error_msg = f"Error fetching data from Jeedom: {response.status_code}"
                print(f"Error: {error_msg}")  # Debug print
                if response.text:
                    print(f"Response text: {response.text}")  # Debug print
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error while connecting to Jeedom: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from Jeedom: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
            
    def save_data_to_file(self, data, filename="jeedom.json"):
        """Save Jeedom data to JSON file"""
        try:
            with open(filename, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)
        except Exception as e:
            error_msg = f"Error saving data to file: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
            
    def load_data_from_file(self, filename="jeedom.json"):
        """Load Jeedom data from JSON file"""
        try:
            with open(filename, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            error_msg = f"File not found: {filename}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in file: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
            
    def print_device_tree(self, data=None):
        """Print formatted device tree"""
        try:
            if data is None:
                data = self.get_full_data()
                
            for x in data:
                print(f"{x['id']}, {x['name']}")
                for eql in x['eqLogics']:
                    print(f"   {eql['id']:3s}, {eql['status']['lastCommunication']} : {Fore.GREEN}{eql['name']}{Style.RESET_ALL}")
                    for cmd in eql['cmds']:
                        print(f"      {cmd['id']:4s}: {cmd['name']} = {Fore.RED}{cmd['state'] if 'state' in cmd else '-'} {cmd.get('unite', '')}{Style.RESET_ALL}")
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
                    
    def get_command_history(self, cmd_id, start_date=None, end_date=None):
        """Get history for a specific command"""
        try:
            url = f"{self.url}/core/api/jeeApi.php"
            
            # Default to last 24 hours if no dates provided
            if not start_date:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Try core API method first
            params = {
                "apikey": self.api_key,
                "type": "history",
                "cmd_id": cmd_id,
                "startTime": start_date,
                "endTime": end_date
            }
            
            print(f"\nTrying core API method with params: {params}")  # Debug print
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10)
                print(f"Response status code: {response.status_code}")  # Debug print
                print(f"Response headers: {response.headers}")  # Debug print
                print(f"Response text: {response.text}")  # Debug print
                
                if response.status_code == 200:
                    if not response.text or response.text.strip() == '[]':
                        print("No history data returned")  # Debug print
                        return []
                    
                    try:
                        data = response.json()
                        print(f"Received history data: {json.dumps(data, indent=2)}")  # Debug print
                        return self._format_history_data(data)
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON: {e}")  # Debug print
                        print(f"Raw response: {response.text}")  # Debug print
                        raise Exception(f"Invalid JSON response from Jeedom: {str(e)}")
                else:
                    error_msg = f"Error fetching command history: {response.status_code}"
                    print(f"Error: {error_msg}")  # Debug print
                    if response.text:
                        print(f"Response text: {response.text}")  # Debug print
                    raise Exception(error_msg)
            except requests.exceptions.RequestException as e:
                error_msg = f"Network error while connecting to Jeedom: {str(e)}"
                print(f"Error: {error_msg}")  # Debug print
                raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            import traceback
            print(traceback.format_exc())  # Debug print stack trace
            raise Exception(error_msg)
            
    def _format_history_data(self, data):
        """Format history data for plotting"""
        formatted_data = []
        
        try:
            if isinstance(data, list):
                for point in data:
                    if isinstance(point, list) and len(point) >= 2:
                        formatted_data.append({
                            'datetime': point[0],
                            'value': float(point[1])
                        })
                    elif isinstance(point, dict):
                        if 'datetime' in point and 'value' in point:
                            formatted_data.append({
                                'datetime': point['datetime'],
                                'value': float(point['value'])
                            })
                        elif 'time' in point and 'value' in point:
                            formatted_data.append({
                                'datetime': point['time'],
                                'value': float(point['value'])
                            })
            elif isinstance(data, dict):
                for timestamp, value in data.items():
                    if isinstance(value, (int, float)):
                        formatted_data.append({
                            'datetime': timestamp,
                            'value': float(value)
                        })
                    elif isinstance(value, dict) and 'value' in value:
                        formatted_data.append({
                            'datetime': timestamp,
                            'value': float(value['value'])
                        })
            
            return sorted(formatted_data, key=lambda x: x['datetime'])
            
        except Exception as e:
            print(f"Error formatting data: {str(e)}")  # Debug print
            print(f"Original data: {data}")  # Debug print
            return []
            
    def get_device_info(self, device_id):
        """Get information for a specific device"""
        try:
            data = self.get_full_data()
            for x in data:
                for eql in x['eqLogics']:
                    if eql['id'] == str(device_id):
                        return eql
            return None
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)

    def get_command_info(self, cmd_id):
        """Get basic information about a command"""
        try:
            url = f"{self.url}/core/api/jeeApi.php"
            params = {
                "apikey": self.api_key,
                "type": "cmd",
                "id": cmd_id
            }
            
            print(f"Getting info for command {cmd_id}")  # Debug print
            response = requests.get(url, params=params)
            print(f"Response status code: {response.status_code}")  # Debug print
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):  # Handle dictionary response
                        print(f"Command info: {data}")  # Debug print
                        if 'logicalId' in data and 'isHistorized' in data:
                            if not data['isHistorized']:
                                print(f"History logging is disabled for command {cmd_id}")  # Debug print
                        return data
                    elif isinstance(data, int):  # Handle integer response
                        print(f"Command ID {data} exists but no additional info available")  # Debug print
                        return {'id': data, 'name': f'Command {data}'}
                    else:
                        print(f"Unexpected command info format: {type(data)}")  # Debug print
                        return None
                except json.JSONDecodeError:
                    print(f"Failed to decode JSON response")  # Debug print
                    return None
            return None
        except Exception as e:
            print(f"Error getting command info: {str(e)}")  # Debug print
            return None
