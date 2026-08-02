"""
Utility functions for MediaPipe Face Mesh landmark processing.
Semua deteksi berbasis multi-frame (sequence) untuk keamanan replay attack.
"""

import numpy as np
from typing import List

# Landmark EAR yang lebih stabil
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
# Indeks hidung untuk tracking posisi kepala
# NOSE_INDEX = 1
NOSE_POINTS = [
    1,   # Nose tip
    2,
    5,
    6
]

# EAR_THRESHOLD = 0.20
# HEAD_THRESHOLD = 0.03
# TURN_THRESHOLD = 0.05
# MIN_FRAMES_CLOSED = 2
EAR_THRESHOLD = 0.18
HEAD_THRESHOLD = 0.025
TURN_THRESHOLD = 0.20
MIN_FRAMES_CLOSED = 2
MIN_FACE_LANDMARKS = 468


def valid_landmarks(landmarks) -> bool:
    """
    Memastikan landmark wajah valid.
    """
    return (
        landmarks is not None
        and len(landmarks) >= MIN_FACE_LANDMARKS
    )
def get_average_nose(landmarks):
    """
    Mengambil rata-rata posisi beberapa landmark hidung.
    Lebih stabil dibanding memakai 1 titik saja.
    """
    xs = []
    ys = []
    zs = []

    for idx in NOSE_POINTS:
        xs.append(landmarks[idx].x)
        ys.append(landmarks[idx].y)
        zs.append(landmarks[idx].z)

    return (
        float(np.mean(xs)),
        float(np.mean(ys)),
        float(np.mean(zs))
    )

def smooth_signal(values, window=3):
    """
    Moving average sederhana untuk mengurangi noise.
    """
    if len(values) < window:
        return values

    smoothed = []

    for i in range(len(values)):
        start = max(0, i - window + 1)
        segment = values[start:i + 1]
        smoothed.append(float(np.mean(segment)))

    return smoothed

def calculate_ear(landmarks, eye_indices: List[int]) -> float:
    """
    Menghitung Eye Aspect Ratio (EAR) dari satu frame.
    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    """
    if not valid_landmarks(landmarks):
        return 0.0
    
    def get(idx):
        return np.array([landmarks[idx].x, landmarks[idx].y])
    
    p1 = get(eye_indices[0])
    p2 = get(eye_indices[1])
    p3 = get(eye_indices[2])
    p4 = get(eye_indices[3])
    p5 = get(eye_indices[4])
    p6 = get(eye_indices[5])
    
    ear = (np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)) / (2 * np.linalg.norm(p1 - p4) + 1e-6)
    return float(ear)

def count_blinks(
    landmarks_sequence: List,
    expected_count: int = 1
):
    """
    Menghitung jumlah kedipan dari sequence EAR.
    Satu kedipan = mata terbuka -> tertutup -> terbuka.
    """

    ears = []

    for lm in landmarks_sequence:

        left = calculate_ear(
            lm,
            LEFT_EYE
        )

        right = calculate_ear(
            lm,
            RIGHT_EYE
        )

        ears.append(
            (left + right) / 2
        )

    # ears = smooth_signal(ears)
    raw_ears = ears.copy()
    ears = smooth_signal(ears)

    print("RAW :", [round(e,3) for e in raw_ears])
    print("SMTH:", [round(e,3) for e in ears])
    print("EAR:", [round(e, 3) for e in ears])
    if len(ears) < 5:
        return 0

    # baseline = np.mean(ears[:5])
    baseline = np.median(ears[:10])

    threshold = baseline * 0.75

    threshold = np.clip(
        baseline * 0.78,
        0.24,
        0.32
    )
    print(
        f"[BLINK] baseline={baseline:.3f} threshold={threshold:.3f}"
    )

    blink_count = 0

    state = "OPEN"

    closed_frames = 0

    for i, ear in enumerate(ears):
        if state == "OPEN":

            if ear <= threshold:

                print(f"Frame {i}: OPEN -> CLOSED")

                state = "CLOSED"

                closed_frames = 1

        elif state == "CLOSED":

            if ear <= threshold:

                closed_frames += 1

            else:

                print(
                    f"Frame {i}: CLOSED -> OPEN "
                    f"(closed={closed_frames})"
                )

                if closed_frames >= MIN_FRAMES_CLOSED:

                    blink_count += 1

                    print("BLINK DETECTED")

                state = "OPEN"

                closed_frames = 0
        # print(
        #     f"Frame {i}: "
        #     f"EAR={ear:.3f} "
        #     f"state={state} "
        #     f"closed={closed_frames}"
        # )
    
    # Jika sequence berakhir saat mata masih tertutup
    if (
        state == "CLOSED"
        and closed_frames >= MIN_FRAMES_CLOSED
    ):
        blink_count += 1
    # print(
    #     f"[BLINK] "
    #     f"expected={expected_count} "
    #     f"detected={blink_count}"
    # )
    return blink_count

def detect_blink(
    landmarks_sequence: List,
    expected_count: int = 1
) -> bool:

    if len(landmarks_sequence) < 5:
        print("[BLINK] ❌ Frame tidak cukup")
        return False

    blink_count = count_blinks(
        landmarks_sequence,
        expected_count
    )

    print(
        f"[BLINK] "
        f"expected={expected_count} "
        f"detected={blink_count}"
    )

    return blink_count >= expected_count

def count_head_nods(
    landmarks_sequence: List,
    threshold: float = HEAD_THRESHOLD
):
    if len(landmarks_sequence) < 5:
        return 0

    ys = []

    for lm in landmarks_sequence:

        if not valid_landmarks(lm):
            return 0

        _, y, _ = get_average_nose(lm)
        ys.append(y)

    ys = smooth_signal(ys)

    baseline = np.mean(ys[:3])

    ENTER_DOWN = threshold
    EXIT_DOWN = threshold * 0.5

    state = "CENTER"

    nod_count = 0

    for y in ys:

        delta = y - baseline

        if state == "CENTER":

            if delta > ENTER_DOWN:

                state = "DOWN"

        elif state == "DOWN":

            if delta < EXIT_DOWN:

                nod_count += 1

                state = "CENTER"

    print(f"[NOD] detected={nod_count}")

    return nod_count
def detect_head_nod(
    landmarks_sequence,
    expected_count=1
):

    nod_count = count_head_nods(
        landmarks_sequence
    )

    print(
        f"[NOD] expected={expected_count} detected={nod_count}"
    )

    return nod_count >= expected_count

def count_head_shakes(
    landmarks_sequence: List,
    threshold: float = HEAD_THRESHOLD
):
    """
    Menghitung jumlah gelengan kepala menggunakan FSM.
    """

    if len(landmarks_sequence) < 5:
        return 0

    xs = []

    for lm in landmarks_sequence:

        if not valid_landmarks(lm):
            return 0

        x, _, _ = get_average_nose(lm)
        xs.append(x)

    xs = smooth_signal(xs)

    baseline = np.mean(xs[:5])

    ENTER = threshold
    EXIT = threshold * 0.7

    state = "CENTER"

    shake_count = 0

    for x in xs:

        delta = x - baseline

        if state == "CENTER":

            if delta > ENTER:
                state = "RIGHT"

            elif delta < -ENTER:
                state = "LEFT"

        elif state == "RIGHT":

            if delta < EXIT:

                shake_count += 1
                state = "CENTER"

        elif state == "LEFT":

            if delta > -EXIT:

                shake_count += 1
                state = "CENTER"

    print(f"[SHAKE] detected={shake_count}")

    return shake_count

def detect_head_shake(
    landmarks_sequence: List,
    expected_count: int = 1
):

    shake_count = count_head_shakes(
        landmarks_sequence
    )

    print(
        f"[SHAKE] "
        f"expected={expected_count} "
        f"detected={shake_count}"
    )

    return shake_count >= expected_count


def detect_turn(
    landmarks_sequence: List,
    direction: str,
    threshold: float = TURN_THRESHOLD
) -> bool:
    """
    Deteksi menoleh ke kiri atau kanan berdasarkan
    perubahan posisi hidung (X) dan rotasi wajah (Z).

    direction:
        - "left"
        - "right"
    """

    if len(landmarks_sequence) < 3:
        print(f"[TURN-{direction.upper()}] ❌ Frame tidak cukup")
        return False

    xs = []
    zs = []

    for lm in landmarks_sequence:

        if not valid_landmarks(lm):
            continue

        x, _, z = get_average_nose(lm)

        xs.append(x)
        zs.append(z)

    # Minimal frame valid
    if len(xs) < 10:
        print("[TURN] ❌ Frame valid terlalu sedikit")
        return False

    xs = smooth_signal(xs)
    zs = smooth_signal(zs)

    # ==========================
    # Baseline
    # ==========================
    BASELINE_FRAMES = max(5, min(8, len(xs) // 4))

    start_x = np.mean(xs[:BASELINE_FRAMES])

    min_x = np.min(xs)
    max_x = np.max(xs)

    movement_x = max_x - min_x
    movement_z = np.max(zs) - np.min(zs)

    # ==========================
    # Validasi gerakan
    # ==========================
    if movement_x < threshold:
        print(
            f"[TURN] ❌ Gerakan X terlalu kecil "
            f"({movement_x:.3f} < {threshold:.3f})"
        )
        return False

    if movement_z < 0.02:
        print(
            f"[TURN] ❌ Rotasi wajah terlalu kecil "
            f"(dz={movement_z:.3f})"
        )
        return False

    # ==========================
    # Hitung arah gerakan
    # ==========================
    if direction == "left":

        movement = start_x - min_x

    elif direction == "right":

        movement = max_x - start_x

    else:
        print("[TURN] ❌ Direction tidak valid")
        return False

    TURN_MARGIN = 0.01

    result = movement >= (threshold - TURN_MARGIN)

    print(
        f"[TURN-{direction.upper()}] "
        f"baseline={start_x:.3f} "
        f"min={min_x:.3f} "
        f"max={max_x:.3f} "
        f"move={movement:.3f} "
        f"dx={movement_x:.3f} "
        f"dz={movement_z:.3f} "
        f"threshold={threshold:.3f} "
        f"result={result}"
    )

    return result


def detect_turn_left(
    landmarks_sequence: List,
    threshold: float = TURN_THRESHOLD
) -> bool:
    return detect_turn(
        landmarks_sequence,
        "left",
        threshold
    )


def detect_turn_right(
    landmarks_sequence: List,
    threshold: float = TURN_THRESHOLD
) -> bool:
    return detect_turn(
        landmarks_sequence,
        "right",
        threshold
    )


def detect_motion(landmarks_sequence: List, challenge: dict) -> bool:
    """
    Wrapper semua challenge.
    challenge:
    {
        "type": "blink",
        "count": 2
    }
    """

    challenge_type = challenge.get("type")

    if challenge_type is None:
        return False
    expected_count = challenge.get("count", 1)

    if challenge_type == "blink":
        return detect_blink(
            landmarks_sequence,
            expected_count
        )

    elif challenge_type == "nod":
        return detect_head_nod(
            landmarks_sequence,
            expected_count
        )

    elif challenge_type == "shake":
        return detect_head_shake(
            landmarks_sequence,
            expected_count
        )

    elif challenge_type == "turn_left":
        return detect_turn_left(
            landmarks_sequence
        )

    elif challenge_type == "turn_right":
        return detect_turn_right(
            landmarks_sequence
        )

    return False