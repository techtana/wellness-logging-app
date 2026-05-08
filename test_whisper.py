"""Quick test: transcribe an audio file with faster-whisper.

Usage:
  python test_whisper.py <audio_file> [model_size] [language] [device]

  model_size : large-v3-turbo (default), large-v3, medium, small, base
  language   : en, th, ja, ...  skips auto-detection (faster, more robust)
               omit or 'auto' to detect automatically
  device     : cpu (default, always works) | cuda | auto
"""
import sys
import time


def register_nvidia_dll_dirs():
    """Add nvidia CUDA wheel bin dirs to the Windows DLL search path.

    Uses sys.path so it works for system Python, venvs, and user installs.
    """
    if sys.platform != "win32":
        return
    import os
    for sp in sys.path:
        nvidia_root = os.path.join(sp, "nvidia")
        if not os.path.isdir(nvidia_root):
            continue
        for pkg in os.listdir(nvidia_root):
            bin_dir = os.path.join(nvidia_root, pkg, "bin")
            if os.path.isdir(bin_dir):
                try:
                    os.add_dll_directory(bin_dir)
                    print(f"  + DLL dir: {bin_dir}")
                except OSError:
                    pass


def load_model(model_size: str, device: str):
    register_nvidia_dll_dirs()
    from faster_whisper import WhisperModel
    # int8 is universally compatible; fp16/float16 crashes on many GPU setups
    print(f"Loading model '{model_size}' on device='{device}' (first run downloads weights)…")
    t0 = time.time()
    model = WhisperModel(model_size, device=device, compute_type="int8")
    print(f"Loaded in {time.time() - t0:.1f}s\n")
    return model


def run_transcription(model, audio_path: str, language: str | None):
    kwargs = {"beam_size": 5}
    if language and language != "auto":
        kwargs["language"] = language

    # language detection (and first encode) happens inside transcribe(), not lazily
    segments_gen, info = model.transcribe(audio_path, **kwargs)

    full_text = []
    for seg in segments_gen:
        full_text.append(seg.text.strip())
        print(f"  [{seg.start:5.1f}s → {seg.end:5.1f}s]  {seg.text.strip()}")

    return full_text, info


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    audio_path = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "large-v3-turbo"
    language   = sys.argv[3] if len(sys.argv) > 3 else None
    device     = sys.argv[4] if len(sys.argv) > 4 else "cpu"

    print(f"Model    : {model_size}")
    print(f"File     : {audio_path}")
    print(f"Language : {language or 'auto-detect'}")
    print(f"Device   : {device}")
    print()

    model = load_model(model_size, device)

    print("Transcribing…")
    t1 = time.time()

    try:
        full_text, info = run_transcription(model, audio_path, language)
    except Exception as e:
        if device != "cpu":
            print(f"\nGPU transcription failed: {e}")
            print("Retrying on CPU…\n")
            model = load_model(model_size, "cpu")
            t1 = time.time()
            full_text, info = run_transcription(model, audio_path, language)
        else:
            raise

    elapsed = time.time() - t1
    print(f"\nDone in {elapsed:.1f}s")
    print(f"Language : {info.language}  (prob {info.language_probability:.2f})")
    print(f"\nFull transcript:\n{' '.join(full_text)}")


if __name__ == "__main__":
    main()
