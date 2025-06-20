import time
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.core.exceptions import HttpResponseError

# --- Azure Configuration ---
# IMPORTANT: Replace with your actual Azure resource details
subscription_id = ""
resource_group = ""
vm_name = ""
public_ip_name = "" # The name of the public IP associated with the VM

# --- Script Configuration ---
# Time to wait in seconds after shutting down the VM before starting it again
WAIT_TIME_MINUTES = 1
WAIT_TIME_SECONDS = WAIT_TIME_MINUTES * 60

def get_credentials():
    """Gets Azure credentials."""
    try:
        return DefaultAzureCredential()
    except Exception as e:
        print(f"Error getting credentials: {e}")
        exit(1)

def get_public_ip(network_client, rg, ip_name):
    """Retrieves the public IP address."""
    print("Attempting to get the public IP address...")
    try:
        ip_address_obj = network_client.public_ip_addresses.get(rg, ip_name)
        ip = ip_address_obj.ip_address
        if ip:
            print(f"Successfully retrieved current IP: {ip}")
        else:
            print("IP address is not assigned yet.")
        return ip
    except HttpResponseError as e:
        print(f"Error getting public IP: {e}")
        return None

def stop_vm(compute_client, rg, vm):
    """Stops (deallocates) the virtual machine."""
    print(f"Deallocating VM '{vm}'...")
    try:
        poller = compute_client.virtual_machines.begin_deallocate(rg, vm)
        poller.wait()
        print(f"VM '{vm}' has been successfully deallocated.")
        return True
    except HttpResponseError as e:
        print(f"Error deallocating VM: {e}")
        return False

def start_vm(compute_client, rg, vm):
    """Starts the virtual machine."""
    print(f"Starting VM '{vm}'...")
    try:
        poller = compute_client.virtual_machines.begin_start(rg, vm)
        poller.wait()
        print(f"VM '{vm}' has been successfully started.")
        return True
    except HttpResponseError as e:
        print(f"Error starting VM: {e}")
        return False

def main():
    """Main function to check IP and manage VM state."""
    # Basic validation of configuration
    if any(val.startswith("YOUR_") for val in [subscription_id, resource_group, vm_name, public_ip_name]):
        print("Please update the script with your Azure subscription, resource group, VM name, and public IP name.")
        return

    print("--- Starting IP Check and VM Management Script ---")
    print(f"Target IP Prefix: 13")
    print(f"VM: {vm_name} in Resource Group: {resource_group}")
    print("-------------------------------------------------")

    credentials = get_credentials()
    compute_client = ComputeManagementClient(credentials, subscription_id)
    network_client = NetworkManagementClient(credentials, subscription_id)

    while True:
        current_ip = get_public_ip(network_client, resource_group, public_ip_name)

        if current_ip and current_ip.startswith("13"):
            print(f"\n✅ Success! Acquired target IP address: {current_ip}")
            print("Script will now terminate.")
            break
        else:
            if current_ip:
                print(f"\n❌ Current IP '{current_ip}' does not match the target '13.x.x.x' prefix.")
            else:
                print("\n❌ Could not retrieve IP or IP is not assigned.")

            # --- VM Restart Cycle ---
            print("Proceeding to restart the VM to acquire a new IP.")

            # Stop the VM
            if not stop_vm(compute_client, resource_group, vm_name):
                print("Failed to stop the VM. Retrying after a short delay.")
                time.sleep(30)
                continue

            # Wait
            print(f"Waiting for {WAIT_TIME_MINUTES} minute(s) before starting again...")
            time.sleep(WAIT_TIME_SECONDS)

            # Start the VM
            if not start_vm(compute_client, resource_group, vm_name):
                 print("Critical error: Failed to start the VM. The script will exit to prevent unexpected costs.")
                 break
            
            print("VM has been restarted. Waiting a moment for the new IP to be assigned...")
            time.sleep(20) # Give Azure time to assign the new IP before the next loop

if __name__ == "__main__":
    main()
