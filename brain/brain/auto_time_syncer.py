#!/usr/bin/env python3
import subprocess
import json
import urllib.request


class AutoTimeSyncer:
    """自动时区同步 + 主动NTP同步"""
    
    def __init__(self, logger):
        self.api_urls = [
            "http://ip-api.com/json/?fields=status,timezone",
            "http://ipwho.is/",
        ]
        self.logger = logger
    
    def _get_timezone(self):
        """通过API获取时区，有备用"""
        for url in self.api_urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode())
                    
                    if 'ip-api.com' in url:
                        if data.get('status') == 'success':
                            return data.get('timezone')
                    elif 'ipwho.is' in url:
                        if data.get('success'):
                            return data.get('timezone').get('id')
            except Exception as e:
                print(e)
                continue
        return None
    
    def _set_timezone(self, tz):
        """设置时区"""
        if not tz:
            return False
        try:
            subprocess.run(['timedatectl', 'set-timezone', tz], check=True, capture_output=True)
            return True
        except:
            return False
    
    def _ntp_sync(self):
        """主动发起NTP时间同步"""
        try:
            subprocess.run(['ntpdate', '-u', 'pool.ntp.org'], check=True, capture_output=True)
            return True
        except:
            return False
    
    def sync(self):
        """同步时区并主动同步时间"""
        tz = self._get_timezone()
        self.logger.info('time sync %s' % tz)
        if tz:
            self._set_timezone(tz)
        return self._ntp_sync()
    
    


