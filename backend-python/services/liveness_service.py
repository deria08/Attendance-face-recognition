import cv2
import numpy as np
import math
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def eye_aspect_ratio(landmarks, eye_indices):
    p1 = landmarks[eye_indices[0]]
    p2 = landmarks[eye_indices[1]]
    p3 = landmarks[eye_indices[2]]
    p4 = landmarks[eye_indices[3]]
    p5 = landmarks[eye_indices[4]]
    p6 = landmarks[eye_indices[5]]
    vertical1 = math.hypot(p2.x - p4.x, p2.y - p4.y)
    vertical2 = math.hypot(p3.x - p5.x, p3.y - p5.y)
    horizontal = math.hypot(p1.x - p6.x, p1.y - p6.y)
    ear = (vertical1 + vertical2) / (2.0 * horizontal)
    return ear

def compute_head_pose(landmarks):
    nose = landmarks[1]
    chin = landmarks[199]
    left_eye_outer = landmarks[33]
    right_eye_outer = landmarks[263]
    nose_chin_vec = (nose.x - chin.x, nose.y - chin.y, nose.z - chin.z)
    pitch = math.degrees(math.atan2(nose_chin_vec[1], math.sqrt(nose_chin_vec[0]**2 + nose_chin_vec[2]**2)))
    eye_center_x = (left_eye_outer.x + right_eye_outer.x) / 2
    yaw = math.degrees(math.atan2(nose.x - eye_center_x, nose.z))
    return yaw, pitch

def detect_head_movement(yaw_list, pitch_list, yaw_thresh=15, pitch_thresh=10):
    if len(yaw_list) < 2:
        return False
    delta_yaw = max(yaw_list) - min(yaw_list)
    delta_pitch = max(pitch_list) - min(pitch_list)
    return delta_yaw > yaw_thresh or delta_pitch > pitch_thresh

def detect_blink_multiframe(images_bytes_list, ear_thresh=0.2, require_head_movement=False):
    ears = []
    yaws = []
    pitches = []

    for idx, img_bytes in enumerate(images_bytes_list):
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            continue
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(img_rgb)
        if not results.multi_face_landmarks:
            continue
        landmarks = results.multi_face_landmarks[0].landmark

        left_eye_indices = [33, 159, 158, 133, 153, 145]   # ganti
        right_eye_indices = [362, 386, 385, 263, 373, 374] # ganti
        ear_left = eye_aspect_ratio(landmarks, left_eye_indices)
        ear_right = eye_aspect_ratio(landmarks, right_eye_indices)
        ear = (ear_left + ear_right) / 2.0
        ears.append(ear)
        print(f"DEBUG EAR frame {idx}: {ear:.4f}")   # tambah debug

        yaw, pitch = compute_head_pose(landmarks)
        yaws.append(yaw)
        pitches.append(pitch)


    print("EARS:", ears)
    print("YAWS:", yaws)
    print("PITCHES:", pitches)
    print("Jumlah frame valid:", len(ears))
    if len(ears) < 10:
        print(f"❌ Liveness: hanya {len(ears)} frame valid (minimal 10)")
        return False
    
    baseline_ear = sum(ears[:2]) / 2
    dynamic_thresh = max(0.2, baseline_ear * 0.9)
    print(f"📊 Baseline EAR: {baseline_ear:.3f}, Threshold: {dynamic_thresh:.3f}")

    state = "OPEN"
    blink_detected = False
    for ear in ears:
        if state == "OPEN" and ear < dynamic_thresh:
            state = "CLOSED"
        elif state == "CLOSED" and ear > dynamic_thresh:
            blink_detected = True
            break
    print(f"EAR={ear:.3f}, STATE={state}")
    if not blink_detected:
        print("❌ Liveness: tidak ada urutan kedipan natural")
        return False

    if require_head_movement:
        head_moved = detect_head_movement(yaws, pitches)
        if not head_moved:
            print("❌ Liveness: gerakan kepala tidak terdeteksi")
        return head_moved
    else:
        print("✅ Liveness berhasil (kedipan terdeteksi)")
        return True