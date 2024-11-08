# logging_config.py
import logging
import logging.handlers
import queue
import sys
import threading
import atexit
import functools


# Create a queue for log records
log_queue = queue.Queue()

# Set up the queue handler and attach it to the root logger
queue_handler = logging.handlers.QueueHandler(log_queue)
root_logger = logging.getLogger()

# root_logger.setLevel(logging.NOTSET)
root_logger.addHandler(queue_handler)

# Set up the listener with desired handlers (e.g., StreamHandler)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter(fmt='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                            datefmt='%Y-%m-%d:%H:%M:%S')
stream_handler.setFormatter(formatter)

# The listener will process log records from the queue using the stream handler
listener = logging.handlers.QueueListener(log_queue, stream_handler)

# # Decorator to log function calls
# def log_debug(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         args_repr = [repr(a) for a in args]
#         kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
#         signature = ", ".join(args_repr + kwargs_repr)
#         root_logger.debug(f"function {func.__name__}() called with args {signature}")
#         try:
#             result = func(*args, **kwargs)
#             return result
#         except Exception as e:
#             root_logger.exception(f"Exception raised in {func.__name__}. exception: {str(e)}")
#             raise e
#     return wrapper


class StdoutRedirector:
    def __init__(self, output_queue):
        self.output_queue = output_queue

    def write(self, message):
        self.output_queue.put(message)

    def flush(self):
        pass  # Required for file-like objects

def output_worker(output_queue):
    while True:
        message = output_queue.get()
        if message == 'STOP':
            break
        try:
            sys.__stdout__.write(message)
            sys.__stdout__.flush()
        except Exception:
            pass  # Handle exceptions as needed
        finally:
            output_queue.task_done()

def start_redirect():
    output_queue = queue.Queue()
    worker_thread = threading.Thread(target=output_worker, args=(output_queue,))
    worker_thread.daemon = True  # Allows the program to exit even if the thread is running
    worker_thread.start()

    # Redirect sys.stdout
    original_stdout = sys.stdout
    sys.stdout = StdoutRedirector(output_queue)

    return output_queue, worker_thread, original_stdout

def stop_redirect(output_queue, worker_thread, original_stdout):
    # Restore sys.stdout
    sys.stdout = original_stdout

    # Signal the worker thread to stop
    output_queue.put('STOP')
    worker_thread.join()

listener.start()
output_queue, worker_thread, original_stdout = start_redirect()

@atexit.register
def redirect_unload():
    stop_redirect(output_queue, worker_thread, original_stdout)
    listener.stop()
    
