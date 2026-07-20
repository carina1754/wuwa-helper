"""공용 테스트 설정 — 콘텐츠 자동 리프레시 차단(테스트 중 실제 네트워크 호출 금지)."""
from __future__ import annotations

import os

os.environ.setdefault("DISABLE_CONTENT_REFRESH", "1")
