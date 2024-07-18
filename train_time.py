import subprocess
import time

def read_header(bus):
    try:
        bridge_control_output = subprocess.check_output(["setpci", "-s", bus, "0e.w"])
        return f" : {bridge_control_output.decode().strip()}"
    except subprocess.CalledProcessError:
        return f"Error reading Bridge Control for {bus}."
    
def read_link_status(bus):
    try:
        link_status_output = subprocess.check_output(["setpci", "-s", bus, "CAP_EXP+0X12.w"])
        return link_status_output.decode().strip()
    except subprocess.CalledProcessError:
        return None
    
def read_link_capabilities(bus):
    try:
        link_capabilities_output = subprocess.check_output(["setpci", "-s", bus, "CAP_EXP+0X0c.l"])
        return link_capabilities_output.decode().strip()
    except subprocess.CalledProcessError:
        print("error")
        return None
    
def hex_to_binary(hex_string):
    binary_string = format(int(hex_string, 16), '032b')
    return binary_string

def extract_link_capabilities(hex_string):
    binary_string = hex_to_binary(hex_string)
    max_link_width = int(binary_string[-3:], 2)
    max_link_speed = int(binary_string[-9:-4], 2)
    return max_link_width, max_link_speed

def extract_link_status(hex_string):
    binary_string = hex_to_binary(hex_string)
    current_link_width = int(binary_string[-4:], 2)
    current_link_speed = int(binary_string[-10:-4:], 2)
    return current_link_width, current_link_speed

def read_secondary_bus_number(bus):
    try:
        secondary_bus_output = subprocess.check_output(["setpci", "-s", bus, "19.b"])
        return secondary_bus_output.decode().strip()
    except subprocess.CalledProcessError:
        return None

def set_bridge_control(bus, value, password):
    try:
        subprocess.run(["sudo", "-S", "setpci", "-s", bus, "3e.w=" + value], input=password.encode(), check=True)
    except subprocess.CalledProcessError:
        print(f"Error setting Bridge Control for {bus}.")

def get_train_time(bdf):
    header_type = read_header(bdf)[-2:]

    if header_type != "01":
        print("Invalid BDF")
        return -1
    
    primary_link_speed_capabilities = read_link_capabilities(bdf)[-1]
    secondary_bus = read_secondary_bus_number(bdf) + ":00.0"
    secondary_link_speed_capabilities =  read_link_capabilities(secondary_bus)[-1]
    train_speed = min(primary_link_speed_capabilities, secondary_link_speed_capabilities)

    primary_link_width_capabilities = hex_to_binary(read_link_capabilities(bdf))[-9:-4]
    secondary_link_width_capabilities =  hex_to_binary(read_link_capabilities(secondary_bus))[-9:-4]
    train_width = min(primary_link_width_capabilities, secondary_link_width_capabilities)

    max_train_time = 0
    for _ in range(10):
        set_bridge_control(bdf, "0043", "Dell1234")
        set_bridge_control(bdf, "0003", "Dell1234")
        start = time.time()
        while(read_link_status(bdf)[-1] != train_speed and hex_to_binary(read_link_status(bdf))[-9:-4] != train_width):
            pass
        end = time.time()
        train_time = end - start
        if train_time > max_train_time:
            max_train_time = train_time

    buffer_time = max_train_time * 1.2
    return buffer_time

def main():
    bdf = "86:00.0"
    print(get_train_time(bdf))

if __name__ == "__main__":
    main()
