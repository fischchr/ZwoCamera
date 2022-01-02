import time
from SubprocessHeader import *
from multiprocessing import Process, Queue
import logging

class Subprocess(Process):
    """A subprocess.

    The counter communicates with the GUI via a communication thread.
    """
    def __init__(self, uid: int, com_queue: Queue, res_queue: Queue):
        """Constructor of the subprocess. 
        
        # Arguments
        * uid::int - Unique ID of the counter
        * com_queue::Queue(int) - Command queue. 
        * res_queue::Queue(tuple) - Result queue for returning the counter value to the GUI. 
                                    Returns a tuple (uid, counter).
        """

        # Call constructor of the parent object
        super(Subprocess, self).__init__()

        # Set UID
        self.uid = uid
        self._timeout = 0.01
        self._running = False

        # Connect the command and result queues
        self.com_queue = com_queue
        self.res_queue = res_queue

        # Make sure the command queue is initially empty
        while not self.com_queue.empty():
            self.com_queue.get()

    def run(self):
        """Eventloop of the subprocess. """

        logging.info(f'Starting event loop of {self}')

        while True:
            # Poll the command queue for self._timeout
            res = self.receive()

            if res is not None:
                # Handle control input from the main program
                if res[0] == CMD_STOP_SUBPROCESS:
                    # Stop the eventloop
                    break
                else:
                    # Handle all other input
                    self.handle_input(res)

            # Run additional code once per iteration
            self.inloop()

        logging.info(f'Stopped event loop of {self}')

    def receive(self):
        """Handle control commands coming from the main program. """

        if self.com_queue.empty():
            time.sleep(self._timeout)
            return None
        else:
            com = self.com_queue.get()
            logging.debug(f'Subrocess {self} received command {com}')
            return com

    def handle_input(self, res):
        """Handle control commands coming from the main program. Can be overwritten by child classes. """

        pass

    def inloop(self):
        """Run additional code once per iteration of the event loop. Can be overwritten by child classes. """

        pass

    def send(self, data: tuple):
        """Send data back to the main process. """

        self.res_queue.put((self.uid, data))


class Interface:
    """Interface for starting and stopping a subprocess and handling the data coming back from it. """

    def __init__(self, uid: int, res_queue: Queue) -> None:
        """Constructor. """

        self.uid = uid
        self.com_queue = Queue()
        self.res_queue = res_queue
        self.subprocess = None

    def init_subprocess(self, uid):
        """Initial the the subprocess. Has to be overwritten by child classes. """

        return Subprocess(uid, self.com_queue, self.res_queue)

    def start_subprocess(self):
        """Start the subprocess if it is not yet running. """

        if self.subprocess is None:
            # Initialize the subprocess
            self.subprocess = self.init_subprocess()

            # Start the subprocess
            logging.info(f'{self} starting subprocess {self.subprocess}')
            self.subprocess.start()

    def stop_subprocess(self, timeout=0.05):
        """Stop the subprocess if it is running. """

        if self.subprocess is not None:
            # Stop the subprocess
            logging.info(f'{self} stopping subprocess {self.subprocess}')
            self.com_queue.put((CMD_STOP_SUBPROCESS, ))

            # Wait for it to fully terminate
            self.subprocess.join()
            self.subprocess = False
            
            # Quickly pause
            time.sleep(timeout)

    def __eq__(self, uid: int) -> bool:
        """Compare the interface by comparing uids. """

        return self.uid == uid

    def handle_data(self, data):
        """Handle data coming from the subprocess. Has to be overwritten by child classes. """

        raise NotImplementedError


class InterfaceManager:
    """Class for managing all interfaces to subprocesses. """

    def __init__(self, *args):
        """Constructor. """

        # Get all interfaces
        self._interfaces = [arg for arg in args]
        logging.debug(f'Initialized {self} with {self._interfaces}')

    def __getitem__(self, uid):
        """Get an interface by UID. """

        index = self._interfaces.index(uid)
        return self._interfaces[index]

    def __iter__(self):
        """Initialize iterator. """

        self.n = 0
        return self

    def __next__(self):
        """Iteration. """

        if self.n < len(self._interfaces):
            # Return the nth interface
            self.n += 1
            return self._interfaces[self.n - 1]
        else:
            raise StopIteration