"""生成自制短音效（22050 Hz 单声道 16-bit WAV），仅用标准库。

来源为程序合成（非商业素材），可在 README 注明「自制音效」。
运行：python tools/gen_sfx.py
"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sfx")


def write_wav(name, samples):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.wav")
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples
        )
        w.writeframes(frames)
    print("wrote", path)


def tone(freq, dur, vol=0.6, decay=True):
    n = int(RATE * dur)
    return [vol * (1 - i / n if decay else 1.0) * math.sin(2 * math.pi * freq * i / RATE)
            for i in range(n)]


def sweep(f0, f1, dur, vol=0.6):
    n = int(RATE * dur)
    out, phase = [], 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / n)
        phase += 2 * math.pi * f / RATE
        out.append(vol * (1 - i / n) * math.sin(phase))
    return out


def noise(dur, vol=0.5):
    n = int(RATE * dur)
    return [vol * (1 - i / n) * (random.random() * 2 - 1) for i in range(n)]


def concat(*parts):
    return [s for p in parts for s in p]


def main():
    write_wav("click", tone(880, 0.05, 0.5))
    write_wav("fly", sweep(300, 900, 0.22, 0.5))
    write_wav("blocked", concat(tone(120, 0.10, 0.7), noise(0.06, 0.4)))
    write_wav("undo", sweep(900, 300, 0.15, 0.45))
    write_wav("clear", concat(tone(523, 0.10, 0.5), tone(659, 0.10, 0.5), tone(784, 0.16, 0.5)))
    write_wav("fail", concat(tone(392, 0.16, 0.5), tone(262, 0.20, 0.5)))


if __name__ == "__main__":
    main()
