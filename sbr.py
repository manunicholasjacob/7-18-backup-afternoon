import subprocess
import time
from datetime import datetime
from train_time import get_train_time

def read_header(bus):
    try:
        bridge_control_output = subprocess.check_output(["setpci", "-s", bus, "0e.w"])
        return f" : {bridge_control_output.decode().strip()}"
    except subprocess.CalledProcessError:
        return f"Error reading Bridge Control for {bus}."

def read_slot_capabilities(bus):
    try:
        slot_capabilities_output = subprocess.check_output(["setpci", "-s", bus, "CAP_EXP+0X14.l"])
        return slot_capabilities_output.decode().strip()
    except subprocess.CalledProcessError:
        return None

def execute_shell_command(command):
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

def hex_to_binary(hex_string):
    binary_string = format(int(hex_string, 16), '032b')
    return binary_string

def read_secondary_bus_number(bus):
    try:
        secondary_bus_output = subprocess.check_output(["setpci", "-s", bus, "19.b"])
        return secondary_bus_output.decode().strip()
    except subprocess.CalledProcessError:
        return None

def read_bridge_control(bus):
    try:
        bridge_control_output = subprocess.check_output(["setpci", "-s", bus, "3e.w"])
        return bridge_control_output.decode().strip()
    except subprocess.CalledProcessError:
        return None

def read_link_status(bus):
    try:
        link_status_output = subprocess.check_output(["setpci", "-s", bus, "CAP_EXP+0X12.w"])
        return link_status_output.decode().strip()
    except subprocess.CalledProcessError:
        return None

def read_link_capabilities17(bus):
    try:
        link_capabilities_output = subprocess.check_output(["setpci", "-s", bus, "CAP_EXP+0X0c.l"])
        return link_capabilities_output.decode().strip()
    except subprocess.CalledProcessError:
        print("error")
        return None

def read_link_capabilities18(bus):
    try:
        link_capabilities_output = subprocess.check_output(["setpci", "-s", bus, "CAP_EXP+0X0c.l"])
        return link_capabilities_output.decode().strip()
    except subprocess.CalledProcessError:
        print("error")
        return None

def set_bridge_control(bus, value, password):
    try:
        subprocess.run(["sudo", "-S", "setpci", "-s", bus, "3e.w=" + value], input=password.encode(), check=True)
    except subprocess.CalledProcessError:
        print(f"Error setting Bridge Control for {bus}.")

def format_bdf(bus):
    bus_number = bus.split(":")[0]
    return f"{bus_number}:0.0"

def convert_hex_to_binary(hex_string):
    decimal_value = int(hex_string, 16)
    binary_string = bin(decimal_value)[2:].zfill(32)
    return binary_string

def extract_link_capabilities(hex_string):
    binary_string = hex_to_binary(hex_string)
    max_link_width = int(binary_string[-3:], 2)
    max_link_speed = int(binary_string[-9:-4], 2)
    return max_link_width, max_link_speed

def read_and_extract_link_capabilities(bus, read_func):
    link_capabilities_hex = read_func(bus)
    return extract_link_capabilities(link_capabilities_hex)

def extract_link_status(hex_string):
    binary_string = hex_to_binary(hex_string)
    current_link_width = int(binary_string[-4:], 2)
    current_link_speed = int(binary_string[-10:-4:], 2)
    return current_link_width, current_link_speed

def get_slot_numbers():
    command_output = execute_shell_command("lspci | cut -d ' ' -f 1")
    split_numbers = [num for num in command_output.split('\n') if num]

    slotnumbers = []
    listbdf = []
    for i in range(len(split_numbers)):
        header = read_header(split_numbers[i])
        if header[-1] == '1':
            a = read_slot_capabilities(split_numbers[i])
            b = hex_to_binary(a)
            c = b[0:13]
            d = int(c, 2)
            if d > 0:
                listbdf.append(split_numbers[i])
                slotnumbers.append(d)
    return [f"{slotnumbers[i]} : {listbdf[i]}" for i in range(len(slotnumbers))]

def display_slot_numbers():
    slot_numbers = get_slot_numbers()
    print("Available slot numbers:")
    for slot in slot_numbers:
        print(slot)

def log_dmidecode_info(log_file):
    try:
        dmidecode_output = subprocess.check_output(["sudo", "dmidecode", "-t", "1"]).decode().strip()
        with open(log_file, 'a') as log:
            log.write(f"\nDMIDecode Output:\n{dmidecode_output}\n")
    except subprocess.CalledProcessError as e:
        with open(log_file, 'a') as log:
            log.write(f"\nError running dmidecode: {str(e)}\n")

def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if iteration == total:
        print()

def run_test(stdscr, user_password, inputnum_loops, kill, slotlist):
    stdscr.addstr(0, 0, "Running the test...\n")
    stdscr.refresh()

    output_lines = []
    start_time = datetime.now()
    output_lines.append(f"Start Time: {start_time}")

    command_output = execute_shell_command("lspci | cut -d ' ' -f 1")
    split_numbers = [num for num in command_output.split('\n') if num]

    slotnumbers = []
    listbdf = []
    for i in range(len(split_numbers)):
        header = read_header(split_numbers[i])
        if header[-1] == '1':
            a = read_slot_capabilities(split_numbers[i])
            b = hex_to_binary(a)
            c = b[0:13]
            d = int(c, 2)
            if d > 0:
                listbdf.append(split_numbers[i])
                slotnumbers.append(d)

    listbdfdown = []
    for i in range(len(listbdf)):
        downstream = listbdf[i]
        secondary_bus = read_secondary_bus_number(downstream)
        a = int(downstream[0:2], 16)
        b = str(hex(a + 1)[2:4])
        c = f"{secondary_bus}:00.0"
        listbdfdown.append(c)

    output_lines.append(f"Tested BDFs: {listbdf}")
    output_lines.append(f"Downstream BDFs: {listbdfdown}")
    output_lines.append(f"Slot Numbers: {slotnumbers}")

    indexlist = []
    bridgecontrollist = []
    link_capabilities = {"upstream": [], "downstream": []}

    max_train_time = 0
    for slot in slotlist:
        idx = slotnumbers.index(slot)
        indexlist.append(idx)
        bridgecontrollist.append(read_bridge_control(listbdf[idx]))
        link_capabilities["upstream"].append(read_and_extract_link_capabilities(listbdf[idx], read_link_capabilities17))
        link_capabilities["downstream"].append(read_and_extract_link_capabilities(listbdfdown[idx], read_link_capabilities18))
        train_time = get_train_time(listbdf[idx])
        if train_time > max_train_time:
            max_train_time = train_time

    num_loops = 2 * inputnum_loops + 1
    total_operations = num_loops * len(indexlist)
    slot_test_count = {slot: 0 for slot in slotlist}

    operation_count = 0
    for i in range(num_loops):
        for j in indexlist:
            operation_count += 1
            slot_test_count[slotnumbers[j]] += 1
            progress_bar(operation_count, total_operations, prefix='Progress', suffix='Complete', length=50)
            specific_bus_bridge = listbdf[j]
            specific_bus_link = listbdfdown[j]
            desired_values = [bridgecontrollist[indexlist.index(j)], "0043"]
            desired_value = desired_values[i % len(desired_values)]
            set_bridge_control(specific_bus_bridge, desired_value, user_password)
            time.sleep(max_train_time)
            if i % 2 == 0:
                current_link_status_hex = read_link_status(specific_bus_link)
                current_link_status = extract_link_status(current_link_status_hex)
                if kill == "n":
                    if current_link_status != link_capabilities["downstream"][indexlist.index(j)]:
                        error_time = datetime.now()
                        output_lines.append(f"Reset {i}")
                        output_lines.append(f"Link status does not match capabilities for bus {specific_bus_link}")
                        output_lines.append(f"Link Status: {current_link_status}")
                        output_lines.append(f"Link Capabilities: {link_capabilities['downstream'][indexlist.index(j)]}")
                        output_lines.append(f"Error Time: {error_time}")
                elif kill == "y":
                    if current_link_status != link_capabilities["downstream"][indexlist.index(j)]:
                        error_time = datetime.now()
                        output_lines.append(f"Reset {i}")
                        output_lines.append(f"Link status does not match capabilities for bus {specific_bus_link}")
                        output_lines.append(f"Link Status: {current_link_status}")
                        output_lines.append(f"Link Capabilities: {link_capabilities['downstream'][indexlist.index(j)]}")
                        output_lines.append(f"Error Time: {error_time}")
                        with open("output.txt", "w") as file:
                            for line in output_lines:
                                file.write(line + "\n")
                        stdscr.addstr(2, 0, "Link status does not match capabilities. Killing the program.")
                        stdscr.refresh()
                        stdscr.getch()
                        return

    end_time = datetime.now()
    output_lines.append(f"End Time: {end_time}")
    output_lines.append(f"Slot Test Counts: {inputnum_loops}")

    with open("output.txt", "w") as file:
        for line in output_lines:
            file.write(line + "\n")

    stdscr.addstr(2, 0, "Test completed. Check the output.txt file for results.")
    stdscr.refresh()
    stdscr.getch()

def run_upstream_sbr(stdscr, user_password, inputnum_loops, kill):
    stdscr.addstr(0, 0, "Running upstream SBR on GPU root ports...\n")
    stdscr.refresh()

    output_lines = []
    start_time = datetime.now()
    output_lines.append(f"Start Time: {start_time}")

    gpu_info_list = gpu_traverse_up()
    root_ports = [gpu_info[2] for gpu_info in gpu_info_list]

    output_lines.append(f"GPU Root Ports: {root_ports}")

    indexlist = list(range(len(root_ports)))
    bridgecontrollist = []
    link_capabilities = {"upstream": [], "downstream": []}

    max_train_time = 0
    for port in root_ports:
        bridgecontrollist.append(read_bridge_control(port))
        link_capabilities["upstream"].append(read_and_extract_link_capabilities(port, read_link_capabilities17))
        train_time = get_train_time(port)
        if train_time > max_train_time:
            max_train_time = train_time

    num_loops = 2 * inputnum_loops + 1
    total_operations = num_loops * len(indexlist)
    port_test_count = {port: 0 for port in root_ports}

    operation_count = 0
    for i in range(num_loops):
        for j in indexlist:
            operation_count += 1
            port_test_count[root_ports[j]] += 1
            progress_bar(operation_count, total_operations, prefix='Progress', suffix='Complete', length=50)
            specific_bus_bridge = root_ports[j]
            desired_values = [bridgecontrollist[indexlist.index(j)], "0043"]
            desired_value = desired_values[i % len(desired_values)]
            set_bridge_control(specific_bus_bridge, desired_value, user_password)
            time.sleep(max_train_time)
            if i % 2 == 0:
                current_link_status_hex = read_link_status(specific_bus_bridge)
                current_link_status = extract_link_status(current_link_status_hex)
                if kill == "n":
                    if current_link_status != link_capabilities["upstream"][indexlist.index(j)]:
                        error_time = datetime.now()
                        output_lines.append(f"Reset {i}")
                        output_lines.append(f"Link status does not match capabilities for bus {specific_bus_bridge}")
                        output_lines.append(f"Link Status: {current_link_status}")
                        output_lines.append(f"Link Capabilities: {link_capabilities['upstream'][indexlist.index(j)]}")
                        output_lines.append(f"Error Time: {error_time}")
                elif kill == "y":
                    if current_link_status != link_capabilities["upstream"][indexlist.index(j)]:
                        error_time = datetime.now()
                        output_lines.append(f"Reset {i}")
                        output_lines.append(f"Link status does not match capabilities for bus {specific_bus_bridge}")
                        output_lines.append(f"Link Status: {current_link_status}")
                        output_lines.append(f"Link Capabilities: {link_capabilities['upstream'][indexlist.index(j)]}")
                        output_lines.append(f"Error Time: {error_time}")
                        with open("output.txt", "w") as file:
                            for line in output_lines:
                                file.write(line + "\n")
                        stdscr.addstr(2, 0, "Link status does not match capabilities. Killing the program.")
                        stdscr.refresh()
                        stdscr.getch()
                        return

    end_time = datetime.now()
    output_lines.append(f"End Time: {end_time}")
    output_lines.append(f"Port Test Counts: {inputnum_loops}")

    with open("output.txt", "w") as file:
        for line in output_lines:
            file.write(line + "\n")

    stdscr.addstr(2, 0, "Test completed. Check the output.txt file for results.")
    stdscr.refresh()
    stdscr.getch()

# Example usage
if __name__ == "__main__":
    display_slot_numbers()
