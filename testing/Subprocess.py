from multiprocessing import Process, Queue
import time
from SubprocessHeader import *



class Subprocess(Process):
    """A subprocess that runs a counter.

    The counter communicates with the GUI via a communication thread.
    """
    def __init__(self, uid: int, com_queue: Queue, out_queue: Queue):
        """Constructor of the subprocess. 
        
        # Arguments
        * uid::int - Unique ID of the counter
        * com_queue::Queue(int) - Command queue. 
        * out_queue::Queue(tuple) - Result queue for returning the counter value to the GUI. 
                                    Returns a tuple (uid, counter).
        """

        # Call constructor of the parent object
        super(Subprocess, self).__init__()

        # Set UID
        self.uid = uid
        self._timeout = 0.01

        # Connect the command and result queues
        self.com_queue = com_queue
        self.out_queue = out_queue

        # Make sure the command queue is initially empty
        while not self.com_queue.empty():
            self.com_queue.get()

    def receive(self):
        if self.com_queue.empty():
            time.sleep(self._timeout)
            return None
        else:
            return self.com_queue.get()

    def send(self, data):
        self.out_queue.put((self.uid, data))

    def handle_input(self, res):
        pass

    def inloop(self):
        pass

    def run(self):
        """Code that runs when the subprocess is started. """

        while True:
            res = self.receive()
            if res is not None:
                if res[0] == CMD_STOP_SUBPROCESS:
                    break
                else:
                    self.handle_input(res)

            self.inloop()


class ProcessManager:
    def __init__(self):
        self.subprocesses = []

    def get_process_index(self, uid):
        index = [process.uid for process in self.subprocesses].index(uid)
        return index

    def __getitem__(self, uid):
        try:
            index = self.get_process_index(uid)
            return self.subprocesses[index]
        except ValueError:
            return None 


    def start_subprocess(self, subprocess: Subprocess):
        uid = subprocess.uid
        
        if self[uid] is None:
            self.subprocesses.append(subprocess)
            self[uid].start()

    def stop_subprocess(self, uid, timeout=0.05):
        if self[uid] is not None:
            # Stop the subprocess
            self[uid].com_queue.put((CMD_STOP_SUBPROCESS, ))
            # Wait for it to fully terminate
            self[uid].join()
            # Erase it from memory (a finished process cannot be restarted)
            index = self.get_process_index(uid)
            self.subprocesses.pop(index)
        
            # Quickly pause
            time.sleep(timeout)

    def stop_all_subprocesses(self):
        uids =  [process.uid for process in self.subprocesses]
        for uid in uids:
            self.stop_subprocess(uid, timeout=0)



class Interface:
    def __init__(self, uid: int, com_queue: Queue, res_queue: Queue) -> None:
        self.uid = uid
        self.command_queue = com_queue
        self.res_queue = res_queue

    def __eq__(self, val: int) -> bool:
        return self.uid == val

    def handle_data(self, data):
        raise NotImplementedError


class InterfaceManager:
    def __init__(self, *args):
        self.interfaces = [arg for arg in args]

    def __getitem__(self, uid):
        index = self.interfaces.index(uid)
        return self.interfaces[index]

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n <= len(self.interfaces):
            return self.interfaces[self.n]
        else:
            raise StopIteration