from gemini.gemini import Gemini
from gemini.logger import Logger as log
from gemini import config
import win32serviceutil
import win32service
import win32event
import threading, pkg_resources, traceback
config.MODE = "LIVE"
config.MIN_PROFIT = 0.0012
config.MIN_REBALANCING_PROFIT = 0.0001
config.PROFIT_ADJUSTMENT = 0.25
config.PROFIT_ADJUSTMENT_REBALANCING = 2.0
config.TICK_TIME = 0.1 # 100ms clock

class GeminiThread(threading.Thread):
    def __init__(self, scheduler):
        self.scheduler = scheduler
        threading.Thread.__init__(self)
    def run(self):
        try:
            self.scheduler.start()
        except Exception as exc:
            log.error(traceback.format_exc())
    def stop(self):
        self.scheduler.exit_flag = True

class GeminiService(win32serviceutil.ServiceFramework):
    _svc_name_ = "Gemini"
    _svc_display_name_ = "Gemini"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        log.ok("Stopped %s Gemini version %s" % (config.MODE, pkg_resources.get_distribution("gemini").version,))

    def SvcDoRun(self):
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            log.ok("Running %s Gemini version %s" % (config.MODE, pkg_resources.get_distribution("gemini").version,))
            bot_thread = GeminiThread(Gemini(config))
            bot_thread.start()
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            bot_thread.stop()
        except Exception as exc:
            log.error("SvcDoRun exception: %s" % (traceback.format_exc(),))

if __name__=='__main__':
    win32serviceutil.HandleCommandLine(GeminiService)