import cv2, mediapipe as mp
hands = mp.solutions.hands.Hands(max_num_hands=1)
draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)   # essayez 1 si 0 ne marche pas
while True:
    ok, frame = cap.read()
    if not ok: break
    frame = cv2.flip(frame, 1)
    res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if res.multi_hand_landmarks:
        draw.draw_landmarks(frame, res.multi_hand_landmarks[0],
                            mp.solutions.hands.HAND_CONNECTIONS)
    cv2.imshow("test", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break
cap.release(); cv2.destroyAllWindows()