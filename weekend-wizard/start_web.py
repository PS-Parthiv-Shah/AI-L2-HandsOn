import subprocess
import os
import sys
import time

def kill_port(port):
    print(f"Checking for processes on port {port}...")
    try:
        # Get PID on port
        cmd = f"netstat -ano | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True).decode()
        for line in output.strip().split('\n'):
            if 'LISTENING' in line:
                pid = line.strip().split()[-1]
                print(f"Terminating process {pid} on port {port}...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, check=False)
                time.sleep(1) # Wait for OS to release socket
    except subprocess.CalledProcessError:
        print(f"Port {port} is clear.")

def start_server():
    kill_port(8000)
    print("Starting Web Agent...")
    
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    web_agent_path = os.path.join(current_dir, "src", "web_agent.py")
    
    # Set PYTHONPATH to include the current directory (for imports within web_agent.py)
    env = os.environ.copy()
    env["PYTHONPATH"] = current_dir + os.pathsep + env.get("PYTHONPATH", "")
    
    # Using sys.executable to ensure same venv
    cmd = [sys.executable, web_agent_path]
    
    try:
        subprocess.run(cmd, cwd=current_dir, env=env)
    except KeyboardInterrupt:
        print("\nStopping server...")

if __name__ == "__main__":
    start_server()
