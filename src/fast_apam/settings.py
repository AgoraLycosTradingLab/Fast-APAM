"""Per-process calculation context, selected explicitly by the runner."""
import json
import os
from datetime import date
from pathlib import Path

path = os.environ.get('FAST_APAM_RUN_CONFIG')
if not path:
    raise RuntimeError('Use the Fast APAM CLI to select a dated snapshot before importing the calculation engine.')
CONFIG = json.loads(Path(path).read_text(encoding='utf-8'))
MODEL_DATE = date.fromisoformat(CONFIG['model_date']).isoformat()
COHORT_SIZE = int(CONFIG['cohort_size'])
WAVE_COUNTS = CONFIG['wave_counts']
if COHORT_SIZE <= 0 or set(WAVE_COUNTS) != {'Wave1', 'Wave2'} or sum(WAVE_COUNTS.values()) != COHORT_SIZE:
    raise ValueError('Invalid snapshot cohort configuration')
