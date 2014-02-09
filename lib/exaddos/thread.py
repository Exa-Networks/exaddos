import sys
import threading

class Thread (threading.Thread):
	def __init__(self, target, queue):
		threading.Thread.__init__(self,target=target)
		self.queue = queue

	def run(self):
		try:
			threading.Thread.run(self)
		except Exception:
			self.queue.put(sys.exc_info())
