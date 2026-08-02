"""
Model untuk Liveness Session menggunakan dataclass (lightweight).
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class LivenessSession:
    session_id: str
    user_id: str
    challenges: List[str]          # 2 challenge acak, e.g. ['blink', 'turn_left']
    current_step: int = 0          # indeks challenge yang sedang dikerjakan
    attempt: int = 0               # percobaan untuk challenge saat ini
    start_time: float = field(default_factory=time.time)
    challenge_start_time: float = field(default_factory=time.time)
    timeout_seconds: int = 12
    max_attempts: int = 3
    completed: bool = False
    failed: bool = False
    completed_at: Optional[float] = None
    failed_at: Optional[float] = None
    
    def get_next_challenge(self) -> Optional[str]:
        """Mengembalikan challenge yang harus dikerjakan, atau None jika selesai."""
        if self.current_step < len(self.challenges):
            return self.challenges[self.current_step]
        return None
    
    def advance(self) -> bool:
        """Pindah ke challenge berikutnya. Return True jika masih ada, False jika selesai."""
        self.current_step += 1
        if self.current_step >= len(self.challenges):
            self.completed = True
            self.completed_at = time.time()
            return False
        # Reset attempt untuk challenge baru
        self.attempt = 0
        self.reset_challenge_timer()
        return True
    
    def is_expired(self) -> bool:
        """Session expired setelah 5 menit."""
        return time.time() - self.start_time > 300  # 5 menit
    
    def is_challenge_timeout(self) -> bool:
        """Challenge timeout setelah timeout_seconds."""
        return time.time() - self.challenge_start_time > self.timeout_seconds
    
    def increment_attempt(self) -> int:
        """Tambah attempt, return jumlah attempt sekarang."""
        self.attempt += 1
        if self.attempt >= self.max_attempts:
            self.failed = True
            self.failed_at = time.time()
        return self.attempt
    
    def mark_failed(self):
        if not self.failed:
            self.failed = True
            self.failed_at = time.time()

    def reset_challenge_timer(self):
        self.challenge_start_time = time.time()

    def remaining_attempts(self) -> int:
        return max(0, self.max_attempts - self.attempt)
    
    def is_active(self):
        return not self.completed and not self.failed and not self.is_expired()
    @property
    def current_challenge(self):
        return self.get_next_challenge()

    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'current_step': self.current_step + 1,
            'total_steps': len(self.challenges),
            'next_challenge': self.get_next_challenge() or '',
            'timeout_seconds': self.timeout_seconds,
            'attempt': self.attempt,
            'remaining_attempts': self.remaining_attempts(),
            'completed': self.completed,
            'failed': self.failed,
        }