from concurrent.futures import ThreadPoolExecutor
from os import cpu_count

_executor = ThreadPoolExecutor(max_workers=cpu_count())  # Global Event Loop Executor
