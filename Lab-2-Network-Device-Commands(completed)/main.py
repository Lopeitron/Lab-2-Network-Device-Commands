import os
import getpass
import logging
from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoAuthenticationException, NetMikoTimeoutException
from paramiko.ssh_exception import SSHException
from ntc_templates.parse import parse_output

def setup_directories():
    """Ensure all required directories exist."""
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data/raw', exist_ok=True)
    os.makedirs('data/reports', exist_ok=True)

def setup_logging():
    """Configure logging to append to logs/lab.log."""
    logging.basicConfig(
        filename='logs/lab.log',
        level=logging.INFO,
        format='%(asctime)s - %(message)s'
    )

def main():
    # Step 2: Log Dev Container Start
    logging.info("[STEP 2] Dev Container Started")

    # Step 3: Collect Credentials Securely
    host = input("Enter device IP or Hostname: ")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    
    logging.info("[CREDENTIALS_COLLECTED]")

    device_params = {
        'device_type': 'cisco_ios',
        'host': host,
        'username': username,
        'password': password,
    }

    # Step 4: Connect to Device with Netmiko
    try:
        net_connect = ConnectHandler(**device_params)
        logging.info("[CONNECT_OK]")
        print(f"Successfully connected to {host}")
    except (AuthenticationException, NetmikoTimeoutException, SSHException, Exception) as e:
        logging.info("[CONNECT_FAIL]")
        print(f"Connection failed: {e}")
        return

    # Step 5 & 6: Run Commands and Parse Output
    commands = [
        "show version",
        "show ip interface brief",
        "show inventory"
    ]
    
    parsed_data = {}

    for cmd in commands:
        # Save raw output
        raw_output = net_connect.send_command(cmd)
        safe_filename = cmd.replace(" ", "_")
        
        with open(f"data/raw/{safe_filename}.txt", "w") as f:
            f.write(raw_output)
        
        logging.info(f"[CMD_RUN:{cmd}]")

        # Parse with NTC Templates
        try:
            parsed_output = parse_output(platform="cisco_ios", command=cmd, data=raw_output)
            if parsed_output:
                parsed_data[cmd] = parsed_output
                logging.info(f"[PARSE_OK:{cmd}]")
            else:
                logging.info(f"[PARSE_FAIL:{cmd}]")
        except Exception as e:
            logging.info(f"[PARSE_FAIL:{cmd}]")
            print(f"Failed to parse '{cmd}': {e}")

    # Step 7: Generate Report and Summary
    try:
        # Extract data safely (ntc_templates returns a list of dictionaries)
        version_data = parsed_data.get("show version", [{}])[0]
        inventory_data = parsed_data.get("show inventory", [{}])[0]
        interfaces_data = parsed_data.get("show ip interface brief", [])

        hostname = version_data.get("hostname", "Unknown")
        version = version_data.get("version", "Unknown")
        model = inventory_data.get("pid", "Unknown") 

        # Format the report string
        report = f"Device Summary for {hostname}\n"
        report += f"{'-'*35}\n"
        report += f"Model:      {model}\n"
        report += f"OS Version: {version}\n\n"
        report += "Interface Statuses:\n"
        
        for intf in interfaces_data:
            name = intf.get("intf", "Unknown")
            status = intf.get("status", "Unknown")
            protocol = intf.get("proto", "Unknown")
            report += f"  - {name:15}: {status} / {protocol}\n"

        # Print to terminal and save to file
        print("\n" + report)
        with open("data/reports/device_summary.txt", "w") as f:
            f.write(report)
            
        logging.info("[REPORT_SAVED]")

    except Exception as e:
        print(f"Error generating report: {e}")

    # Step 9: Close SSH session gracefully
    net_connect.disconnect()

# Step 8: Implement the Direct Execution Check
if __name__ == "__main__":
    setup_directories()
    setup_logging()
    
    logging.info("[LAB2-START]")
    main()
    logging.info("[LAB2-END]")