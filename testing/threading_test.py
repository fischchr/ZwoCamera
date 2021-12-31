from threading import Thread
import time


def foo(var):
    for i in range(10):
        if i % 2:
            var['a'] = i
        else:
            var['b'] = i
        time.sleep(0.2)

v = {'a': 0, 'b': 0}
t = Thread(target=foo, args=(v,))
t.start()
for i in range(20):
    print(v)
    time.sleep(0.1)

t.join()