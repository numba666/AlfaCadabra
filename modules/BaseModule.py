import subprocess
import threading
import os
import time

class BaseModule:
    def __init__(self, interface: str):
        self.interface = interface
        self.process = None
        self.output_buffer = []
        self.error_buffer = []
        self.status = "idle" # idle, running, finished, error
        self.results = {}
        self.thread = None # For GUI integration, to run in a separate thread

    def _run_command(self, command: list, capture_output: bool = True, wait: bool = True):
        """
        Internal method to run a shell command.
        Handles process creation and basic output capture.
        """
        try:
            if wait:
                result = subprocess.run(command, capture_output=capture_output, text=True, check=True)
                if capture_output:
                    self.output_buffer.append(result.stdout)
                    self.error_buffer.append(result.stderr)
                self.status = "finished"
                return result
            else:
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
                self.status = "running"
                # For non-blocking read, you'd typically have a separate thread consuming these pipes
                return self.process
        except FileNotFoundError:
            self.status = "error"
            self.error_buffer.append(f"Error: Command '{command[0]}' not found. Is it installed and in PATH?")
            print(f"Error: Command '{command[0]}' not found. Is it installed and in PATH?")
            return None
        except subprocess.CalledProcessError as e:
            self.status = "error"
            self.error_buffer.append(f"Error executing command: {e}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
            print(f"Error executing command: {e.cmd}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
            return None
        except Exception as e:
            self.status = "error"
            self.error_buffer.append(f"An unexpected error occurred: {e}")
            print(f"An unexpected error occurred: {e}")
            return None

    def start(self, *args, **kwargs):
        """Starts the module's operation."""
        raise NotImplementedError("Subclasses must implement 'start' method.")

    def stop(self):
        """Stops the module's operation."""
        if self.process and self.process.poll() is None: # Check if process is still running
            print(f"Terminating process for {self.__class__.__name__}...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5) # Give it some time to terminate gracefully
            except subprocess.TimeoutExpired:
                self.process.kill() # Force kill if it doesn't terminate
                print(f"Process for {self.__class__.__name__} force killed.")
            self.status = "stopped"
            print(f"Module {self.__class__.__name__} stopped.")
        elif self.process:
            print(f"Process for {self.__class__.__name__} was already finished or stopped.")
        else:
            print(f"No process was started for {self.__class__.__name__}.")

    def get_status(self):
        """Returns the current status of the module."""
        return self.status

    def get_results(self):
        """Returns the results collected by the module."""
        return self.results

    def get_output(self):
        """Returns the raw stdout/stderr from the executed command."""
        return "\n".join(self.output_buffer), "\n".join(self.error_buffer)

    def _clear_buffers(self):
        self.output_buffer = []
        self.error_buffer = []

    # --- Methods for GUI integration (to be called from GUI thread) ---
    def start_threaded(self, *args, **kwargs):
        """Starts the module's operation in a separate thread."""
        self.status = "starting"
        self._clear_buffers()
        self.thread = threading.Thread(target=self.start, args=args, kwargs=kwargs)
        self.thread.daemon = True # Allow the main program to exit even if thread is running
        self.thread.start()

    def stop_threaded(self):
        """Stops the module's operation, potentially from a separate thread."""
        if self.thread and self.thread.is_alive():
            self.stop()
            # It's generally not safe to join a thread that's still potentially performing I/O
            # Best is to signal the thread to exit cleanly if possible, or rely on terminate/kill.
        elif self.thread:
            print("Module thread was not alive or not started.")
