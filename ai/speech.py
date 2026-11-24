"""Bounded decoding through PyAV, CPU ASR with segment confidence (not clinical certainty)."""
import os
import time
from functools import lru_cache
from pathlib import Path
import av
import numpy as np

MAX_BYTES = 25 * 1024 * 1024
MAX_SECONDS = 600


def load_audio(path):
    path = Path(path)
    if path.suffix.lower() not in {'.wav', '.mp3', '.m4a', '.ogg', '.flac'}:
        raise ValueError('Unsupported audio extension.')
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError('Audio must be nonempty and at most 25 MB.')
    chunks = []
    count = 0
    try:
        with av.open(str(path)) as container:
            resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
            for frame in container.decode(audio=0):
                for converted in resampler.resample(frame):
                    samples = converted.to_ndarray().flatten()
                    count += len(samples)
                    if count > MAX_SECONDS * 16000:
                        raise ValueError('Audio exceeds 10 minutes.')
                    chunks.append(samples)
            for converted in resampler.resample(None):
                chunks.append(converted.to_ndarray().flatten())
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Audio could not be decoded.') from exc
    if not chunks:
        raise ValueError('No audio samples found.')
    audio = np.concatenate(chunks).astype(np.float32) / 32768
    if len(audio) > MAX_SECONDS*16000:
        raise ValueError('Audio exceeds 10 minutes.')
    if np.sqrt(np.mean(audio ** 2)) < 0.0001:
        raise ValueError('Audio contains only silence.')
    return audio


@lru_cache(maxsize=1)
def model(name, device, compute):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device=device, compute_type=compute, cpu_threads=4)


def transcribe(path):
    started = time.perf_counter()
    audio = load_audio(path)
    segments, info = model(os.getenv('ACI_ASR_MODEL', 'tiny.en'), os.getenv('ACI_ASR_DEVICE', 'cpu'),
                           os.getenv('ACI_ASR_COMPUTE', 'int8')).transcribe(audio, language='en', beam_size=5,
                                                                         vad_filter=True)
    data = [{'start': s.start, 'end': s.end, 'text': s.text.strip(), 'avg_logprob': s.avg_logprob,
             'no_speech_prob': s.no_speech_prob} for s in segments]
    text = ' '.join(s['text'] for s in data)
    if not text.strip():
        raise ValueError('No speech recognized.')
    return {'path': str(path), 'transcript': text, 'segments': data,
            'processing_seconds': time.perf_counter()-started, 'audio_seconds': len(audio)/16000,
            'language': info.language, 'speaker_warning': 'ASR does not identify speakers. Add Doctor:/Patient: labels during correction.'}
