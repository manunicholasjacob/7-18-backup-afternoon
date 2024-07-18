import subprocess
from datetime import datetime
import time
import curses

def output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = ""):
    pady, padx = window.getyx()
    window.addstr(pady+1, 0, input)
    if pady+1 > window_height-4:
        pad_pos += int(len(input)/window_width) + 1
    window.refresh(pad_pos, 0, window_offset_y, window_offset_x, window_height, window_width)
    return pad_pos

def execute_shell_command(command):
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return result.stdout.decode("utf-8").strip()
        else:
            return f"Error: {result.stderr.decode('utf-8').strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

def check_replay(gpu_percentage, burn_time, gpu_number, gpu_index, call_time, window, window_offset_y, window_offset_x, window_height, window_width, pad_pos):
    try:
        pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "Starting gpu_burn...")
        gpu_process = subprocess.Popen(['./gpu_burn', '-d', '-m', f"{gpu_percentage}%", f"{burn_time}"], cwd="/home/NVIDIA/gpu_burn-1.1/gpu-burn", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "running in background")
    except Exception as e:
        return f"Error: {str(e)}"

    replay_count = ""
    while gpu_process.poll() is None:
        now = datetime.now()
        pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"Current Timestamp: {now}")
        if(len(gpu_index) > 0):
            for index in gpu_index:
                pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"GPU {index}:")
                replay_count = execute_shell_command(f"nvidia-smi -i {index} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count:
                    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"{line.strip()}")
                    time.sleep(1)
        else:
            for i in range(gpu_number):
                pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"GPU {i}:")
                replay_count = execute_shell_command(f"nvidia-smi -i {i} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count:
                    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = f"{line.strip()}")
        time.sleep(call_time)

    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "gpu_burn has completed.")
    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "Writing to gpu_burn_output.txt")
    bdf_read = execute_shell_command("nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader")
    bdf_read = bdf_read.split('\n')
    bdf_read = [":".join(line.split(':')[1:]) for line in bdf_read]
    with open("./gpu_burn_output.txt", "w") as file:
        if(len(gpu_index) > 0):
            bdfs = []
            for i, bdf in enumerate(bdf_read):
                if i in gpu_index: bdfs.append(bdf)
            for i, bdf in enumerate(bdfs):
                file.write(f"GPU {gpu_index[i]} - " + bdf + ":\n")
                replay_count = execute_shell_command(f"nvidia-smi -i {gpu_index[i]} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: file.write(line.strip() + "\n")
                file.write("\n")
        else:
            for gpu_index_tag, bdf in enumerate(bdf_read):
                file.write(f"GPU {gpu_index_tag} - " + bdf + ":\n")
                replay_count = execute_shell_command(f"nvidia-smi -i {gpu_index_tag} -q|grep -i replay")
                replay_count = replay_count.split("\n")
                for line in replay_count: file.write(line.strip() + "\n")
                file.write("\n")
    pad_pos = output_print(window, window_offset_y, window_offset_x, window_height, window_width, pad_pos, input = "Writing to gpu_burn_log.txt")
    stdout, stderr = gpu_process.communicate()
    with open("./gpu_burn_log.txt", "w") as file:
        file.write(stdout.decode("utf-8"))

    return pad_pos

def read_class_code(bdf):
    return execute_shell_command(f"lspci -s {bdf} -n | awk '{{print $3}}'")

def read_header(bdf):
    return execute_shell_command(f"setpci -s {bdf} HEADER_TYPE")

def read_secondary_bus_number(bdf):
    return execute_shell_command(f"setpci -s {bdf} SECONDARY_BUS")

def read_slot_capabilities(bdf):
    try:
        slot_capabilities_output = subprocess.check_output(["setpci", "-s", bdf, "CAP_EXP+0X14.l"])
        return slot_capabilities_output.decode().strip()
    except subprocess.CalledProcessError:
        return None

def hex_to_binary(hex_string):
    binary_string = format(int(hex_string, 16), '032b')
    return binary_string

def identify_gpus():
    command_output = execute_shell_command("lspci | cut -d ' ' -f 1")
    bdf_list = [num for num in command_output.split('\n') if num]

    gpus = []
    for bdf in bdf_list:
        class_code = read_class_code(bdf)
        header_type = read_header(bdf)
        if class_code and class_code[:2] == '03' and header_type[-2:] == '00':
            gpus.append(bdf)
    return gpus

def trace_to_root_port(bdf):
    current_bus = bdf.split(":")[0]
    while True:
        upstream_connection = None
        all_bdfs = execute_shell_command("lspci | cut -d ' ' -f 1").split('\n')
        header_bdfs = [b for b in all_bdfs if read_header(b).strip()[-2:] == "01"]
        for header_bdf in header_bdfs:
            if read_secondary_bus_number(header_bdf) == current_bus:
                upstream_connection = header_bdf
                break
        if not upstream_connection:
            return bdf  # Return the current BDF if no upstream connection is found
        current_bus = upstream_connection.split(":")[0]
        bdf = upstream_connection

def gpu_traverse_up():
    gpus = identify_gpus()
    root_ports = [trace_to_root_port(gpu) for gpu in gpus]

    gpu_info_list = []
    for gpu, root_port in zip(gpus, root_ports):
        physical_slot_number = read_slot_capabilities(root_port)
        slot_number = int(hex_to_binary(physical_slot_number)[:13], 2)
        gpu_info_list.append([gpu, slot_number, root_port])
    
    return gpu_info_list

def run_command(command):
    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()
    if result.returncode != 0:
        raise Exception(f"Command failed with error: {stderr.decode('utf-8')}")
    return stdout.decode('utf-8')

def get_bdf_list():
    output = run_command("lspci")
    bdf_list = [line.split()[0] for line in output.splitlines()]
    return bdf_list

def get_vendor_bdf_list(vendor_id):
    output = run_command(f"lspci -d {vendor_id}:")
    vendor_bdf_list = [line.split()[0] for line in output.splitlines()]
    return vendor_bdf_list

def get_header_type(bdf):
    header_type = run_command(f"setpci -s {bdf} HEADER_TYPE")
    return header_type.strip()

def main():
    check_replay(burn_time=10, gpu_number=4)
    print(gpu_traverse_up())

if __name__ == "__main__":
    main()
