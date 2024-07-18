import functions
import subprocess

def main():
    try:
        # Execute the shell command
        functions.run_command("sudo modprobe -r nvidia_uvm")
        functions.run_command("sudo modprobe -r nvidia_drm")
        diag_process = subprocess.Popen(['./fieldiag'], cwd="/home/dell/Downloads/629-INT16-UNIV-ALL", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = diag_process.communicate()
        with open("./629_diag_output.txt", "w") as file:
            file.write(stdout.decode("utf-8"))
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    main()
