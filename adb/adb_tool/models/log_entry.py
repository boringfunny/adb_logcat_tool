"""日志条目模型"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List
import re


class LogLevel(Enum):
    VERBOSE = "V"
    DEBUG = "D"
    INFO = "I"
    WARNING = "W"
    ERROR = "E"
    FATAL = "F"
    SILENT = "S"
    UNKNOWN = "?"
    
    @property
    def display_name(self) -> str:
        names = {
            "V": "Verbose",
            "D": "Debug",
            "I": "Info",
            "W": "Warning",
            "E": "Error",
            "F": "Fatal",
            "S": "Silent",
            "?": "Unknown"
        }
        return names.get(self.value, "Unknown")


@dataclass
class LogEntry:
    timestamp: Optional[datetime]
    pid: int
    tid: int
    level: LogLevel
    tag: str
    message: str
    raw_line: str
    
    LOG_PATTERN = re.compile(
        r'^(\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d+)\s+(\d+)\s+(\d+)\s+([VDIWEFS?])\s+(\S+)\s*:\s*(.*)$'
    )
    
    @classmethod
    def parse(cls, line: str) -> Optional['LogEntry']:
        line = line.strip()
        if not line:
            return None
        
        match = cls.LOG_PATTERN.match(line)
        if match:
            timestamp_str, pid_str, tid_str, level_str, tag, message = match.groups()
            
            try:
                timestamp = datetime.strptime(f"1970-{timestamp_str}", "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                timestamp = None
            
            try:
                level = LogLevel(level_str)
            except ValueError:
                level = LogLevel.UNKNOWN
            
            return cls(
                timestamp=timestamp,
                pid=int(pid_str),
                tid=int(tid_str),
                level=level,
                tag=tag,
                message=message,
                raw_line=line
            )
        
        return cls(
            timestamp=None,
            pid=0,
            tid=0,
            level=LogLevel.UNKNOWN,
            tag="",
            message=line,
            raw_line=line
        )
    
    def matches_filter(
        self,
        tag: Optional[str] = None,
        level: Optional[LogLevel] = None,
        levels: Optional[List[LogLevel]] = None,
        keyword: Optional[str] = None,
        pid: Optional[int] = None
    ) -> bool:
        if tag and tag.upper() not in self.tag.upper():
            return False
        
        if levels is not None and self.level not in levels:
            return False
        
        if level and self.level != level:
            return False
        
        if keyword and keyword.lower() not in self.message.lower():
            return False
        
        if pid and self.pid != pid:
            return False
        
        return True
    
    @property
    def formatted_line(self) -> str:
        if self.timestamp:
            time_str = self.timestamp.strftime("%m-%d %H:%M:%S.%f")[:-3]
            return f"{time_str} [{self.level.value}] {self.tag}: {self.message}"
        return self.raw_line
