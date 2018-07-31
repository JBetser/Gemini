# file and command prompt colorama logger
from . import config
import os, time, threading
from colorama import Fore

class Logger:
    init = False
    write_lock = threading.Lock()
    last_error = None

    def warning(msg):
        Logger._write(Fore.YELLOW, msg)

    def error(msg):
        Logger.last_error = msg
        Logger._write(Fore.RED, msg)

    def ok(msg):
        Logger._write(Fore.GREEN, msg)

    def info(msg):
        Logger._write(Fore.RESET, msg)

    def _write(level, msg):
        t = time.strftime('%b %d, %Y %X')
        if os.name == 'nt' and config.IS_SERVICE:
            Logger._windows_log(level, msg)
        else:
            with Logger.write_lock:
                with open(os.path.abspath(os.path.join(config.LOG_DIR, config.LOG_FILENAME)), "a") as log_file:
                    log_file.write("%s : %s\r\n" % (t, msg))
                print("%s%s : %s%s" % (level, t, msg, Fore.RESET))

    def _windows_log(level, msg):
        import win32api
        import win32con
        import win32evtlog
        import win32security
        import win32evtlogutil

        applicationName = "CryptoBot"
        ph = win32api.GetCurrentProcess()
        th = win32security.OpenProcessToken(ph, win32con.TOKEN_READ)
        my_sid = win32security.GetTokenInformation(th, win32security.TokenUser)[0]

        category = 5	# arbitrary value
        msg = str(msg)
        if level == Fore.YELLOW:
            eventID = 2
            myType = win32evtlog.EVENTLOG_WARNING_TYPE
            descr = [msg]
        elif level == Fore.RED:
            eventID = 3
            myType = win32evtlog.EVENTLOG_ERROR_TYPE
            descr = [msg]
        elif level == Fore.GREEN:
            eventID = 0
            myType = win32evtlog.EVENTLOG_SUCCESS
            descr = [msg]
        else:
            eventID = 1
            myType = win32evtlog.EVENTLOG_INFORMATION_TYPE
            descr = [msg]

        win32evtlogutil.ReportEvent(applicationName, eventID, eventCategory=category,
        	eventType=myType, strings=descr, sid=my_sid)